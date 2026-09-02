import time
import paho.mqtt.client as mqtt
import globals as gl
from mongo import MongoDBManager
from sensores import SensorManager

# ==========================================
# 1. INICIALIZACIÓN DE MÓDULOS
# ==========================================
db = MongoDBManager()
sensor = SensorManager()
estado_actual = gl.ESTADO_NORMAL

# ==========================================
# 2. EVENTOS MQTT
# ==========================================
def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("[MQTT] Conectado a EMQX exitosamente.")
        client.subscribe(f"{gl.TOPIC_BASE}/control/remoto")
    else:
        print(f"[MQTT] Error de conexión. Código: {reason_code}")

def on_message(client, userdata, msg):
    comando = msg.payload.decode('utf-8')
    print(f"\n[COMANDO REMOTO] Tópico: {msg.topic} | Acción: {comando}")
    # Guardar el comando remoto en MongoDB
    db.col_commands.insert_one({
        "comando": comando, 
        "timestamp": db.get_timestamp()
    })

# Configuración del Cliente MQTT
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"Backend_{gl.CARNE}")
client.on_connect = on_connect
client.on_message = on_message

print(f"Conectando a broker {gl.BROKER}...")
client.connect(gl.BROKER, gl.PORT, 60)
client.loop_start()  # Inicia un hilo en segundo plano para manejar red sin bloquear el while

# ==========================================
# 3. BUCLE PRINCIPAL (MÁQUINA DE ESTADOS)
# ==========================================
try:
    print("[SISTEMA] Iniciando monitorización del Edificio Inteligente...\n")
    # Forzar el primer registro de estado en la nube
    db.update_system_status(estado_actual)
    
    while True:
        # 1. Leer Sensores
        temp = sensor.leer_temperatura()
        hum = sensor.leer_humedad()
        gas = sensor.leer_gas()
        dist = sensor.leer_distancia()
        luz = sensor.leer_luz()

        # 2. Publicar en MQTT
        client.publish(f"{gl.TOPIC_BASE}/sensores/temperatura", temp)
        client.publish(f"{gl.TOPIC_BASE}/sensores/humedad", hum)
        client.publish(f"{gl.TOPIC_BASE}/sensores/gas", gas)
        client.publish(f"{gl.TOPIC_BASE}/sensores/distancia", dist)
        client.publish(f"{gl.TOPIC_BASE}/sensores/luz", luz)

        # 3. Persistencia en MongoDB
        db.insert_sensor_reading("temperatura", temp)
        db.insert_sensor_reading("humedad", hum)
        db.insert_sensor_reading("gas", gas)
        db.insert_sensor_reading("distancia", dist)
        db.insert_sensor_reading("luz", luz)

        # 4. Lógica de Estados Globales
        nuevo_estado = gl.ESTADO_NORMAL

        if gas > gl.UMBRAL_GAS_PELIGRO:
            nuevo_estado = gl.ESTADO_EMERGENCIA
        elif temp > gl.UMBRAL_TEMP_ALTA or not (gl.UMBRAL_HUMEDAD_MIN <= hum <= gl.UMBRAL_HUMEDAD_MAX):
            nuevo_estado = gl.ESTADO_ADVERTENCIA

        # Solo registrar si hay un cambio de estado
        if nuevo_estado != estado_actual:
            print(f">>> [ALERTA] Cambio de estado: {estado_actual} -> {nuevo_estado}")
            db.update_system_status(nuevo_estado)
            db.insert_event("CAMBIO_ESTADO", f"El sistema pasó a {nuevo_estado}")
            client.publish(f"{gl.TOPIC_BASE}/estado/global", nuevo_estado)
            estado_actual = nuevo_estado
        
        print(f"Lecturas -> Temp: {temp}C | Hum: {hum}% | Gas: {gas} | Estado: {estado_actual}")

        # Generar dinámicamente el archivo para ARM64 y reescribirlo
        sensor.generar_archivo_arm64(20)

        # ==========================================
        # 5. PUENTE ARM64 (Lectura de resultados)
        # ==========================================
        try:
            # En el futuro, aquí agregaremos: os.system("./programa_arm64")
            
            with open("resultado.txt", "r", encoding="utf-8") as file:
                lineas = file.readlines()
                
            # Extraer solo los valores numéricos limpiando el formato "CLAVE=VALOR"
            max_val = int(lineas[0].split("=")[1].strip())
            min_val = int(lineas[1].split("=")[1].strip())
            avg_val = int(lineas[2].split("=")[1].strip())
            count_val = int(lineas[3].split("=")[1].strip())
            
            # Guardar en base de datos
            db.insert_arm64_result(max_val, min_val, avg_val, count_val)
            
            # Publicar al Dashboard
            payload_arm64 = f"MAX:{max_val},MIN:{min_val},AVG:{avg_val},COUNT:{count_val}"
            client.publish(f"{gl.TOPIC_BASE}/arm64/resultados", payload_arm64)
            print(f"[ARM64] Resultados procesados -> {payload_arm64}")
            
        except Exception as e:
            print(f"[ARM64] Esperando resultados del módulo ensamblador... Error: {e}")

        # Esperar 5 segundos para el siguiente ciclo
        time.sleep(5)

except KeyboardInterrupt:
    print("\n[SISTEMA] Apagado solicitado por el usuario...")
    client.loop_stop()
    client.disconnect()