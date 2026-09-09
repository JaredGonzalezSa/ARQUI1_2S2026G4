import time
import subprocess
import os
import paho.mqtt.client as mqtt
import globals as gl
from mongo import MongoDBManager
from core.sensores import SensorManager
from core.actuadores import ActuadorManager
from arm64_integracion import procesar_arm64

# ==========================================
# 1. INICIALIZACIÓN DE MÓDULOS
# ==========================================
db = MongoDBManager()
sensor = SensorManager()
actuador = ActuadorManager()

estado_actual = gl.ESTADO_NORMAL
actuador.actualizar_estado(estado_actual)

contador_ciclos = 0
# Ciclos para guardar en base de datos 1 ciclo = 5s
CICLOS_PARA_MONGODB = 2

ultimo_boton = {'boton1': 0, 'boton2': 0, 'boton3': 0, 'boton4': 0}
DEBOUNCE_MS = 300

ultimo_estado_puerta = None

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
    
    # ==========================================
    # COMANDOS REMOTOS (según el PDF)
    # ==========================================
    
    # ABRIR_PUERTA: Mueve el servomotor a posición abierta por 5 segundos
    if comando == "ABRIR_PUERTA":
        actuador.abrir_puerta_temporal()
        db.insert_event("COMANDO", "Puerta abierta remotamente")
        client.publish(f"{gl.TOPIC_BASE}/actuadores/puerta", "ABIERTA")
    
    # CERRAR_PUERTA: Fuerza el cierre inmediato
    elif comando == "CERRAR_PUERTA":
        actuador.cerrar_puerta()
        db.insert_event("COMANDO", "Puerta cerrada remotamente")
        client.publish(f"{gl.TOPIC_BASE}/actuadores/puerta", "CERRADA")
    
    # TOGGLE_PUERTA: Alterna el estado de la puerta
    elif comando == "TOGGLE_PUERTA":
        actuador.toggle_puerta()
        estado = "ABIERTA" if actuador.puerta_abierta else "CERRADA"
        db.insert_event("COMANDO", f"Puerta {estado} remotamente")
        client.publish(f"{gl.TOPIC_BASE}/actuadores/puerta", estado)
    
    # ENCENDER_LUCES: Enciende las 3 zonas de iluminación
    elif comando == "ENCENDER_LUCES":
        actuador.encender_luces()
        db.insert_event("COMANDO", "Luces ON remotamente")
        client.publish(f"{gl.TOPIC_BASE}/actuadores/luces", "ON")
    
    # APAGAR_LUCES: Apaga las 3 zonas de iluminación
    elif comando == "APAGAR_LUCES":
        actuador.apagar_luces()
        db.insert_event("COMANDO", "Luces OFF remotamente")
        client.publish(f"{gl.TOPIC_BASE}/actuadores/luces", "OFF")
    
    # TOGGLE_LUCES: Alterna el estado de las luces
    elif comando == "TOGGLE_LUCES":
        actuador.toggle_luces()
        estado = "ON" if actuador.luces_encendidas else "OFF"
        db.insert_event("COMANDO", f"Luces {estado} remotamente")
        client.publish(f"{gl.TOPIC_BASE}/actuadores/luces", estado)
    
    # MODO_AUTO: Reactiva la lógica automática de iluminación
    elif comando == "MODO_AUTO":
        actuador.set_modo_luz(True)
        db.insert_event("COMANDO", "Modo AUTO")
        client.publish(f"{gl.TOPIC_BASE}/actuadores/luces", "MODO_AUTO")
    
    # MODO_MANUAL: Desactiva el encendido automático
    elif comando == "MODO_MANUAL":
        actuador.set_modo_luz(False)
        db.insert_event("COMANDO", "Modo MANUAL")
        client.publish(f"{gl.TOPIC_BASE}/actuadores/luces", "MODO_MANUAL")
    
    # SILENCIAR_ALARMA: Apaga el buzzer
    elif comando == "SILENCIAR_ALARMA":
        actuador.silenciar_alarma()
        db.insert_event("COMANDO", "Alarma silenciada")
        client.publish(f"{gl.TOPIC_BASE}/actuadores/alarma", "SILENCIADA")
    
    # RESTABLECER_ALERTA: Apaga el buzzer solo si el gas bajó
    elif comando == "RESTABLECER_ALERTA":
        gas_actual = sensor.leer_gas()
        if gas_actual <= gl.UMBRAL_GAS_PELIGRO:
            actuador.desactivar_alarma()
            db.insert_event("COMANDO", "Alerta restablecida")
            client.publish(f"{gl.TOPIC_BASE}/actuadores/alarma", "RESTABLECIDA")
        else:
            db.insert_event("COMANDO", "Intento fallido: gas aún peligroso")
    
    # TOGGLE_VENTILADOR: Alterna el ventilador
    elif comando == "TOGGLE_VENTILADOR":
        actuador.toggle_ventilador()
        estado = "ON" if actuador.ventilador_encendido else "OFF"
        db.insert_event("COMANDO", f"Ventilador {estado}")
        client.publish(f"{gl.TOPIC_BASE}/actuadores/ventilador", estado)

# ==========================================
# 3. CONFIGURACIÓN MQTT
# ==========================================
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"Backend_{gl.CARNE}")
client.on_connect = on_connect
client.on_message = on_message

print(f"Conectando a broker {gl.BROKER}...")
client.connect(gl.BROKER, gl.PORT, 60)
client.loop_start()

# ==========================================
# 4. BUCLE PRINCIPAL
# ==========================================
try:
    print("[SISTEMA] Iniciando monitorización del Edificio Inteligente...\n")
    db.update_system_status(estado_actual)
    
    while True:
        # ==========================================
        # 4.1 LEER SENSORES
        # ==========================================
        temp = sensor.leer_temperatura()
        hum = sensor.leer_humedad()
        gas = sensor.leer_gas()
        dist = sensor.leer_distancia()
        luz = sensor.leer_luz()
        
        # ==========================================
        # 4.2 PUBLICAR EN MQTT
        # ==========================================
        client.publish(f"{gl.TOPIC_BASE}/sensores/temperatura", temp)
        client.publish(f"{gl.TOPIC_BASE}/sensores/humedad", hum)
        client.publish(f"{gl.TOPIC_BASE}/sensores/gas", gas)
        client.publish(f"{gl.TOPIC_BASE}/sensores/distancia", dist)
        client.publish(f"{gl.TOPIC_BASE}/sensores/luz", luz)
        
        # ==========================================
        # 4.3 PERSISTENCIA EN MONGODB (cada N ciclos)
        # ==========================================
        contador_ciclos += 1
        if contador_ciclos >= CICLOS_PARA_MONGODB:
            db.insert_sensor_reading("temperatura", temp)
            db.insert_sensor_reading("humedad", hum)
            db.insert_sensor_reading("gas", gas)
            db.insert_sensor_reading("distancia", dist)
            db.insert_sensor_reading("luz", luz)
            contador_ciclos = 0
        
        # ==========================================
        # 4.4 LÓGICA DE ESTADOS GLOBALES
        # ==========================================
        nuevo_estado = gl.ESTADO_NORMAL
        
        if gas > gl.UMBRAL_GAS_PELIGRO:
            nuevo_estado = gl.ESTADO_EMERGENCIA
            
            # Activar alarma solo si cambió el estado (o no está silenciada)
            if nuevo_estado != estado_actual:
                actuador.activar_alarma()
            
            # ⚠️ IMPORTANTE: La puerta DEBE abrirse CADA VEZ que hay emergencia
            # (no solo cuando cambia el estado)
            actuador.abrir_puerta_temporal()
            db.insert_event("EMERGENCIA", f"Gas peligroso: {gas}")
            client.publish(f"{gl.TOPIC_BASE}/actuadores/alarma", "ON")
            client.publish(f"{gl.TOPIC_BASE}/actuadores/puerta", "ABIERTA_AUTO")
        
        # ADVERTENCIA: Temperatura alta o humedad fuera de rango
        elif temp > gl.UMBRAL_TEMP_ALTA or not (gl.UMBRAL_HUMEDAD_MIN <= hum <= gl.UMBRAL_HUMEDAD_MAX):
            nuevo_estado = gl.ESTADO_ADVERTENCIA
            
            if temp > gl.UMBRAL_TEMP_ALTA:
                actuador.encender_ventilador()
                db.insert_event("ADVERTENCIA", f"Temp alta: {temp}°C")
                client.publish(f"{gl.TOPIC_BASE}/actuadores/ventilador", "ON")
            else:
                actuador.apagar_ventilador()
                client.publish(f"{gl.TOPIC_BASE}/actuadores/ventilador", "OFF")
            
            if not (gl.UMBRAL_HUMEDAD_MIN <= hum <= gl.UMBRAL_HUMEDAD_MAX):
                db.insert_event("ADVERTENCIA", f"Humedad fuera de rango: {hum}%")
        
        # NORMAL: Todo en orden
        else:
            actuador.apagar_ventilador()
            client.publish(f"{gl.TOPIC_BASE}/actuadores/ventilador", "OFF")
            
            # Si salimos de emergencia automáticamente
            if estado_actual == gl.ESTADO_EMERGENCIA and gas <= gl.UMBRAL_GAS_PELIGRO:
                actuador.desactivar_alarma()
                client.publish(f"{gl.TOPIC_BASE}/actuadores/alarma", "OFF")
                db.insert_event("NORMAL", "Saliendo de EMERGENCIA")
        
        # ==========================================
        # 4.5 CAMBIO DE ESTADO
        # ==========================================
        if nuevo_estado != estado_actual:
            print(f">>> [ALERTA] Cambio de estado: {estado_actual} -> {nuevo_estado}")
            db.update_system_status(nuevo_estado)
            db.insert_event("CAMBIO_ESTADO", f"El sistema pasó a {nuevo_estado}")
            client.publish(f"{gl.TOPIC_BASE}/estado/global", nuevo_estado)
            actuador.actualizar_estado(nuevo_estado)
            estado_actual = nuevo_estado
        
        # ==========================================
        # 4.6 CONTROL DE ILUMINACIÓN AUTOMÁTICA
        # ==========================================
        # NOTA: Valor ALTO = oscuridad, valor BAJO = iluminado
        if actuador.modo_luz_auto:
            if luz > gl.UMBRAL_LUZ_BAJA:
                actuador.encender_luces()
                client.publish(f"{gl.TOPIC_BASE}/actuadores/luces", "AUTO_ON")
                print(f"Luz oscura ({luz}) -> Luces ON")
            else:
                actuador.apagar_luces()
                client.publish(f"{gl.TOPIC_BASE}/actuadores/luces", "AUTO_OFF")
                print(f"Luz suficiente ({luz}) -> Luces OFF")
        
        # ==========================================
        # 4.7 CONTROL DE PUERTA POR DISTANCIA
        # ==========================================
        if dist < gl.UMBRAL_DISTANCIA_APERTURA and not actuador.puerta_abierta:
            actuador.abrir_puerta_temporal()
            db.insert_event("PUERTA", f"Apertura por distancia: {dist}cm")
            client.publish(f"{gl.TOPIC_BASE}/actuadores/puerta", "ABIERTA_AUTO")
        
        # ==========================================
        # 4.8 LECTURA DE BOTONES FÍSICOS
        # ==========================================
        botones = actuador.leer_botones()
        t_actual_ms = time.time() * 1000

        # Botón 1 - Toggle puerta
        if botones.get('boton1', False) and (t_actual_ms - ultimo_boton['boton1'] > DEBOUNCE_MS):
            actuador.toggle_puerta()
            estado_puerta = "ABIERTA" if actuador.puerta_abierta else "CERRADA"
            db.insert_event("BOTON", f"Botón 1: Puerta {estado_puerta}")
            client.publish(f"{gl.TOPIC_BASE}/actuadores/puerta", estado_puerta)
            ultimo_boton['boton1'] = t_actual_ms

        # Botón 2 - Toggle modo luz
        if botones.get('boton2', False) and (t_actual_ms - ultimo_boton['boton2'] > DEBOUNCE_MS):
            modo = actuador.toggle_modo_luz()
            modo_str = "AUTOMATICO" if modo else "MANUAL"
            db.insert_event("BOTON", f"Botón 2: Modo {modo_str}")
            client.publish(f"{gl.TOPIC_BASE}/control/remoto", f"MODO_{modo_str}")
            ultimo_boton['boton2'] = t_actual_ms

        # Botón 3 - Silenciar alarma
        if botones.get('boton3', False) and (t_actual_ms - ultimo_boton['boton3'] > DEBOUNCE_MS):
            actuador.silenciar_alarma()
            db.insert_event("BOTON", "Botón 3: Alarma silenciada")
            client.publish(f"{gl.TOPIC_BASE}/actuadores/alarma", "SILENCIADA")
            ultimo_boton['boton3'] = t_actual_ms

        # Botón 4 - Restablecer alerta
        if botones.get('boton4', False) and (t_actual_ms - ultimo_boton['boton4'] > DEBOUNCE_MS):
            if sensor.leer_gas() <= gl.UMBRAL_GAS_PELIGRO:
                actuador.desactivar_alarma()
                db.insert_event("BOTON", "Botón 4: Alerta restablecida")
                client.publish(f"{gl.TOPIC_BASE}/actuadores/alarma", "RESTABLECIDA")
            else:
                db.insert_event("BOTON", "Botón 4: No se puede restablecer - gas peligroso")
            ultimo_boton['boton4'] = t_actual_ms
        
        # ==========================================
        # 4.9 MOSTRAR CONSOLA
        # ==========================================
        print(f"Lecturas -> Temp:{temp}°C Hum:{hum}% Gas:{gas} Dist:{dist}cm Luz:{luz} | Estado:{estado_actual}")
        print(f"Actuadores -> Puerta:{'ABI' if actuador.puerta_abierta else 'CER'} Luces:{'ON' if actuador.luces_encendidas else 'OFF'} Vent:{'ON' if actuador.ventilador_encendido else 'OFF'} Alarma:{'ON' if actuador.alarma_activada else 'OFF'}")
        
        # ==========================================
        # 4.10 ARM64: GENERAR ARCHIVO Y PROCESAR
        # ==========================================
        sensor.generar_archivo_arm64(20)
        
        try:
            resultado = procesar_arm64()
            
            max_val = resultado["max"]
            min_val = resultado["min"]
            avg_val = resultado["avg"]
            count_val = resultado["count"]
            
            # Guardar en MongoDB
            db.insert_arm64_result(max_val, min_val, avg_val, count_val)
            
            # Publicar al Dashboard
            payload_arm64 = f"MAX:{max_val},MIN:{min_val},AVG:{avg_val},COUNT:{count_val}"
            client.publish(f"{gl.TOPIC_BASE}/arm64/resultados", payload_arm64)
            print(f"[ARM64] Resultados procesados -> {payload_arm64}")
            
        except Exception as e:
            print(f"[ARM64] Error ejecutando módulo ensamblador: {e}")
        
        # ==========================================
        # PUBLICAR ESTADO DE PUERTA
        # ==========================================
        estado_puerta_actual = "ABIERTA" if actuador.puerta_abierta else "CERRADA"

        if estado_puerta_actual != ultimo_estado_puerta:
            ultimo_estado_puerta = estado_puerta_actual
            client.publish(f"{gl.TOPIC_BASE}/actuadores/puerta", estado_puerta_actual)
            print(f"[MQTT] Puerta: {estado_puerta_actual}")
        
        # ==========================================
        # 4.11 ESPERAR AL SIGUIENTE CICLO
        # ==========================================
        time.sleep(gl.CICLO_PRINCIPAL)

except KeyboardInterrupt:
    print("\n[SISTEMA] Apagado solicitado por el usuario...")
    client.loop_stop()
    client.disconnect()

finally:
    if 'actuador' in locals():
        del actuador
    if 'sensor' in locals():
        del sensor
    print("Sistema finalizado.")