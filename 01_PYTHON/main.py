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
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("[MQTT] Conectado a EMQX exitosamente.")
        # Suscribirnos a los comandos que vengan del Dashboard
        client.subscribe(f"{gl.TOPIC_BASE}/control/remoto")
    else:
        print(f"[MQTT] Error de conexión. Código: {rc}")

def on_message(client, userdata, msg):
    comando = msg.payload.decode('utf-8')
    print(f"\n[COMANDO REMOTO] Tópico: {msg.topic} | Acción: {comando}")
    # Guardar el comando remoto en MongoDB
    db.col_commands.insert_one({
        "comando": comando, 
        "timestamp": db.get_timestamp()
    })

# Configuración del Cliente MQTT
client = mqtt.Client(client_id=f"Backend_{gl.CARNE}")
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

        # Esperar 5 segundos para el siguiente ciclo
        time.sleep(5)

except KeyboardInterrupt:
    print("\n[SISTEMA] Apagado solicitado por el usuario...")
    client.loop_stop()
    client.disconnect()