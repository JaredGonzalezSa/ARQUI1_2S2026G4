import time
import paho.mqtt.client as mqtt
import globals as gl
from mongo import MongoDBManager
from sensores import SensorManager
from actuadores import ActuadorManager 

# ==========================================
# 1. INICIALIZACIÓN DE MÓDULOS
# ==========================================
db = MongoDBManager()
sensor = SensorManager(puerto_serial=gl.PUERTO_SERIAL)
estado_actual = gl.ESTADO_NORMAL
actuador = ActuadorManager(serial_conexion=sensor.serial_conexion)

estado_actual = gl.ESTADO_NORMAL
actuador.actualizar_estado(estado_actual) 

# Contador para MongoDB se envia cada N ciclos
contador_ciclos = 0
CICLOS_PARA_MONGODB = 6

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

    # Ejecutar comando remoto (se puede expandir según necesidad)
    if comando == "ABRIR_PUERTA":
        actuador.abrir_puerta_temporal()
    elif comando == "CERRAR_PUERTA":
        actuador.cerrar_puerta()
    elif comando == "ENCENDER_LUCES":
        actuador.encender_luces()
    elif comando == "APAGAR_LUCES":
        actuador.apagar_luces()
    elif comando == "MODO_AUTO":
        actuador.set_modo_luz(True)
    elif comando == "MODO_MANUAL":
        actuador.set_modo_luz(False)
    elif comando == "SILENCIAR_ALARMA":
        actuador.desactivar_alarma()
    elif comando == "RESTABLECER_ALERTA":
        # Solo si ya no hay emergencia
        if sensor.leer_gas() <= gl.UMBRAL_GAS_PELIGRO:
            actuador.desactivar_alarma()
            db.insert_event("COMANDO", "Alertas restablecidas remotamente")

# Configuración del Cliente MQTT
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"Backend_{gl.CARNE}")
client.on_connect = on_connect
client.on_message = on_message

print(f"Conectando a broker {gl.BROKER}...")
client.connect(gl.BROKER, gl.PORT, 60)
client.loop_start()  # Hilo en segundos plano para MQTT

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
        botones = actuador.leer_botones()

        # 2. Publicar en MQTT
        client.publish(f"{gl.TOPIC_BASE}/sensores/temperatura", temp)
        client.publish(f"{gl.TOPIC_BASE}/sensores/humedad", hum)
        client.publish(f"{gl.TOPIC_BASE}/sensores/gas", gas)
        client.publish(f"{gl.TOPIC_BASE}/sensores/distancia", dist)
        client.publish(f"{gl.TOPIC_BASE}/sensores/luz", luz)

        # 3. Persistencia en MongoDB
        contador_ciclos += 1
        if contador_ciclos >= CICLOS_PARA_MONGODB:
            db.insert_sensor_reading("temperatura", temp)
            db.insert_sensor_reading("humedad", hum)
            db.insert_sensor_reading("gas", gas)
            db.insert_sensor_reading("distancia", dist)
            db.insert_sensor_reading("luz", luz)
            contador_ciclos = 0

        # 4. Lógica de Estados Globales
        nuevo_estado = gl.ESTADO_NORMAL

        if gas > gl.UMBRAL_GAS_PELIGRO:
            nuevo_estado = gl.ESTADO_EMERGENCIA
            actuador.activar_alarma()       # Activa buzzer
            actuador.abrir_puerta_temporal()# Evacuación automática        
        elif temp > gl.UMBRAL_TEMP_ALTA or not (gl.UMBRAL_HUMEDAD_MIN <= hum <= gl.UMBRAL_HUMEDAD_MAX):
            nuevo_estado = gl.ESTADO_ADVERTENCIA

            if temp > gl.UMBRAL_TEMP_ALTA:
                actuador.encender_ventilador()
            else:
                actuador.apagar_ventilador()
        else:
            actuador.apagar_ventilador()    

        # Solo registrar si hay un cambio de estado
        if nuevo_estado != estado_actual:
            print(f">>> [ALERTA] Cambio de estado: {estado_actual} -> {nuevo_estado}")
            db.update_system_status(nuevo_estado)
            db.insert_event("CAMBIO_ESTADO", f"El sistema pasó a {nuevo_estado}")
            client.publish(f"{gl.TOPIC_BASE}/estado/global", nuevo_estado)
            actuador.actualizar_estado(nuevo_estado)

            estado_actual = nuevo_estado
        
        # Control de iluminación automática
        if actuador.modo_luz_auto:
            if luz < gl.UMBRAL_LUZ_BAJA:
                actuador.encender_luces()
            else:
                actuador.apagar_luces()

        # Control de puerta por distancia
        if dist < gl.UMBRAL_DISTANCIA_APERTURA and not actuador.puerta_abierta:
            actuador.abrir_puerta_temporal()
            db.insert_event("PUERTA", f"Apertura por detección a {dist}cm")


        # Botones físicos
        if botones['boton1']:
            actuador.toggle_puerta()
            db.insert_event("BOTON", "Botón 1: toggle puerta")
        if botones['boton2']:
            actuador.toggle_modo_luz()
            db.insert_event("BOTON", "Botón 2: toggle modo luz")
        if botones['boton3']:
            actuador.desactivar_alarma()
            db.insert_event("BOTON", "Botón 3: silenciar alarma")
        if botones['boton4']:
            if gas <= gl.UMBRAL_GAS_PELIGRO:
                actuador.desactivar_alarma()
                db.insert_event("BOTON", "Botón 4: restablecer alerta")

        # Actualizar LCD
        linea1 = f"T:{temp}C H:{hum}%"
        if estado_actual == gl.ESTADO_EMERGENCIA:
            linea2 = "*** EMERGENCIA ***"
        elif estado_actual == gl.ESTADO_ADVERTENCIA:
            linea2 = "*** ADVERTENCIA ***"
        else:
            linea2 = f"G:{gas} D:{dist}cm"
        actuador.actualizar_lcd(linea1, linea2)

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


finally:
    del actuador
    del sensor
    print("[SISTEMA] Recursos liberados.")