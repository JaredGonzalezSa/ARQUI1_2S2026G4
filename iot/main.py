import time
import subprocess
import os
import sys
import paho.mqtt.client as mqtt

backend_path = os.path.join(os.path.dirname(__file__), '..', 'backend')
sys.path.insert(0, backend_path)

from mongo import MongoDBManager
import globals as gl
from core.sensores import SensorManager
from core.actuadores import ActuadorManager
from arm64_integracion import procesar_arm64
ultimo_estado_luces_auto = None
ultimo_estado_ventilador_auto = None


# ==========================================
# 1. INICIALIZACION DE MODULOS
# ==========================================
db = MongoDBManager()
sensor = SensorManager()
actuador = ActuadorManager()

estado_actual = gl.ESTADO_NORMAL
actuador.actualizar_estado(estado_actual)

contador_ciclos = 0
CICLOS_PARA_MONGODB = 20

ultimo_boton = {'boton1': 0, 'boton2': 0, 'boton3': 0, 'boton4': 0}
DEBOUNCE_MS = 150
ultimo_estado_puerta = None
ultimo_estado_luces_auto = None
ultimo_estado_ventilador_auto = None

# ==========================================
# 2. EVENTOS MQTT
# ==========================================
def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("[MQTT] Conectado a EMQX exitosamente.")
        client.subscribe(f"{gl.TOPIC_BASE}/control/remoto")
    else:
        print(f"[MQTT] Error de conexion. Codigo: {reason_code}")

def on_message(client, userdata, msg):
    comando = msg.payload.decode('utf-8')
    print(f"\n[COMANDO REMOTO] Topico: {msg.topic} | Accion: {comando}")
    
    db.col_commands.insert_one({
        "comando": comando,
        "timestamp": db.get_timestamp()
    })
    
    # PUERTA
    if comando == "ABRIR_PUERTA":
        actuador.abrir_puerta_temporal()
        db.insert_event("COMANDO", "Puerta abierta remotamente")
        client.publish(f"{gl.TOPIC_BASE}/actuadores/puerta", "ABIERTA", retain=True)
        print(f"[PUERTA] Estado publicado: ABIERTA")

    elif comando == "CERRAR_PUERTA":
        actuador.cerrar_puerta()
        db.insert_event("COMANDO", "Puerta cerrada remotamente")
        client.publish(f"{gl.TOPIC_BASE}/actuadores/puerta", "CERRADA", retain=True)
        print(f"[PUERTA] Estado publicado: CERRADA")

    elif comando == "TOGGLE_PUERTA":
        actuador.toggle_puerta()
        estado = "ABIERTA" if actuador.puerta_abierta else "CERRADA"
        db.insert_event("COMANDO", f"Puerta {estado} remotamente")
        client.publish(f"{gl.TOPIC_BASE}/actuadores/puerta", estado, retain=True)
    # LUCES
    elif comando == "ENCENDER_LUCES":
        actuador.set_modo_luz(False)
        actuador.encender_luces()
        db.insert_event("COMANDO", "Luces ON remotamente")
        client.publish(f"{gl.TOPIC_BASE}/actuadores/luces", "ON", retain=True)
        client.publish(f"{gl.TOPIC_BASE}/actuadores/luces", "MODO_MANUAL", retain=True)

    elif comando == "APAGAR_LUCES":
        actuador.set_modo_luz(False)
        actuador.apagar_luces()
        db.insert_event("COMANDO", "Luces OFF remotamente")
        client.publish(f"{gl.TOPIC_BASE}/actuadores/luces", "OFF", retain=True)
        client.publish(f"{gl.TOPIC_BASE}/actuadores/luces", "MODO_MANUAL", retain=True)
    
    elif comando == "TOGGLE_LUCES":
        actuador.toggle_luces()
        estado = "ON" if actuador.luces_encendidas else "OFF"
        db.insert_event("COMANDO", f"Luces {estado} remotamente")
        client.publish(f"{gl.TOPIC_BASE}/actuadores/luces", estado, retain=True)
        client.publish(f"{gl.TOPIC_BASE}/actuadores/luces", "MODO_MANUAL", retain=True)
    
    # MODO ILUMINACION
    elif comando == "MODO_AUTO":
        actuador.set_modo_luz(True)
        db.insert_event("COMANDO", "Modo AUTO")
        client.publish(f"{gl.TOPIC_BASE}/actuadores/luces", "MODO_AUTO", retain=True)
    
    elif comando == "MODO_MANUAL":
        actuador.set_modo_luz(False)
        db.insert_event("COMANDO", "Modo MANUAL")
        client.publish(f"{gl.TOPIC_BASE}/actuadores/luces", "MODO_MANUAL", retain=True)
    
    # ALARMA
    elif comando == "SILENCIAR_ALARMA":
        actuador.silenciar_alarma()
        db.insert_event("COMANDO", "Alarma silenciada")
        client.publish(f"{gl.TOPIC_BASE}/actuadores/alarma", "SILENCIADA", retain=True)
    
    elif comando == "RESTABLECER_ALERTA":
        gas_actual = sensor.leer_gas()
        if gas_actual <= gl.UMBRAL_GAS_PELIGRO:
            actuador.desactivar_alarma()
            db.insert_event("COMANDO", "Alerta restablecida")
            client.publish(f"{gl.TOPIC_BASE}/actuadores/alarma", "RESTABLECIDA", retain=True)
        else:
            db.insert_event("COMANDO", "Intento fallido: gas aun peligroso")
    
    # VENTILADOR
    elif comando == "TOGGLE_VENTILADOR":
        actuador.set_modo_ventilador(False)
        actuador.toggle_ventilador()
        estado = "ON" if actuador.ventilador_encendido else "OFF"
        db.insert_event("COMANDO", f"Ventilador {estado}")
        client.publish(f"{gl.TOPIC_BASE}/actuadores/ventilador", estado, retain=True)

# ==========================================
# 3. CONFIGURACION MQTT
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
    print("\n" + "="*60)
    print("SISTEMA EDIFICIO INTELIGENTE IoT")
    print("="*60)
    print(f"Broker MQTT:  {gl.BROKER}")
    print(f"Base de datos: MongoDB Atlas")
    print(f"Ciclo:         {gl.CICLO_PRINCIPAL}s")
    print("="*60 + "\n")
    
    db.update_system_status(estado_actual)
    
    # ==========================================
    # VARIABLES DE CONTROL DE TIEMPO
    # ==========================================
    ultimo_ciclo_temp = time.time()
    ultimo_ciclo_hum = time.time()
    ultimo_ciclo_gas = time.time()
    ultimo_ciclo_dist = time.time()
    ultimo_ciclo_luz = time.time()
    ultimo_lcd = time.time()
    ultimo_arm64 = time.time()
    
    INTERVALO_TEMP = 2.0
    INTERVALO_HUM = 2.0
    INTERVALO_GAS = 1.0
    INTERVALO_DIST = 0.5
    INTERVALO_LUZ = 1.0
    INTERVALO_LCD = 2.0
    INTERVALO_ARM64 = 10

    temp = 0
    hum = 0
    gas = 0
    dist = 0
    luz = 0
    
    pantalla_lcd = 0
    PANTALLAS_LCD = 6
    
        # ==========================================
    # LECTURA INICIAL DE SENSORES
    # ==========================================
    print("[SISTEMA] Realizando lectura inicial de sensores...")
    temp = sensor.leer_temperatura()
    hum = sensor.leer_humedad()
    gas = sensor.leer_gas()
    dist = sensor.leer_distancia()
    luz = sensor.leer_luz()
    
    # Publicar sensores con retain=True
    client.publish(f"{gl.TOPIC_BASE}/sensores/temperatura", temp, retain=True)
    client.publish(f"{gl.TOPIC_BASE}/sensores/humedad", hum, retain=True)
    client.publish(f"{gl.TOPIC_BASE}/sensores/gas", gas, retain=True)
    client.publish(f"{gl.TOPIC_BASE}/sensores/distancia", dist, retain=True)
    client.publish(f"{gl.TOPIC_BASE}/sensores/luz", luz, retain=True)
    
    # Publicar estado inicial de actuadores con retain=True
    db.update_system_status(estado_actual)
    client.publish(f"{gl.TOPIC_BASE}/estado/global", estado_actual, retain=True)
    
    estado_puerta_ini = "ABIERTA" if actuador.puerta_abierta else "CERRADA"
    estado_luces_ini = "ON" if actuador.luces_encendidas else "OFF"
    estado_vent_ini = "ON" if actuador.ventilador_encendido else "OFF"
    estado_alarma_ini = "ON" if actuador.alarma_activada else "OFF"
    
    client.publish(f"{gl.TOPIC_BASE}/actuadores/puerta", estado_puerta_ini, retain=True)
    client.publish(f"{gl.TOPIC_BASE}/actuadores/luces", estado_luces_ini, retain=True)
    client.publish(f"{gl.TOPIC_BASE}/actuadores/ventilador", estado_vent_ini, retain=True)
    client.publish(f"{gl.TOPIC_BASE}/actuadores/alarma", estado_alarma_ini, retain=True)
    
    print(f"[SISTEMA] Lectura inicial: Temp:{temp}C Hum:{hum}% Gas:{gas} Dist:{dist}cm Luz:{luz}")
    
    # Actualizar LCD inicial
    linea1 = f"T:{temp}C H:{hum}%"
    if estado_actual == gl.ESTADO_EMERGENCIA:
        linea2 = "*** EMERGENCIA ***"
    elif estado_actual == gl.ESTADO_ADVERTENCIA:
        linea2 = "*** ADVERTENCIA ***"
    else:
        linea2 = f"G:{gas} D:{dist}cm"
    actuador.actualizar_lcd(linea1, linea2)

    while True:
        tiempo_actual = time.time()
        
        # ==========================================
        # LECTURA DE SENSORES (INDIVIDUAL)
        # ==========================================
        if tiempo_actual - ultimo_ciclo_temp >= INTERVALO_TEMP:
            ultimo_ciclo_temp = tiempo_actual
            temp = sensor.leer_temperatura()
            client.publish(f"{gl.TOPIC_BASE}/sensores/temperatura", temp)
        
        if tiempo_actual - ultimo_ciclo_hum >= INTERVALO_HUM:
            ultimo_ciclo_hum = tiempo_actual
            hum = sensor.leer_humedad()
            client.publish(f"{gl.TOPIC_BASE}/sensores/humedad", hum)
        
        if tiempo_actual - ultimo_ciclo_gas >= INTERVALO_GAS:
            ultimo_ciclo_gas = tiempo_actual
            gas = sensor.leer_gas()
            client.publish(f"{gl.TOPIC_BASE}/sensores/gas", gas)
        
        if tiempo_actual - ultimo_ciclo_dist >= INTERVALO_DIST:
            ultimo_ciclo_dist = tiempo_actual
            dist = sensor.leer_distancia()
            client.publish(f"{gl.TOPIC_BASE}/sensores/distancia", dist)
        
        if tiempo_actual - ultimo_ciclo_luz >= INTERVALO_LUZ:
            ultimo_ciclo_luz = tiempo_actual
            luz = sensor.leer_luz()
            client.publish(f"{gl.TOPIC_BASE}/sensores/luz", luz)
        
        # ==========================================
        # LECTURA DE BOTONES (SIN DEBOUNCE DUPLICADO)
        # ==========================================
        botones = actuador.leer_botones()
        t_actual_ms = time.time() * 1000

        # Boton 1 - Toggle puerta
        if botones.get('boton1', False):
            if actuador.puerta_abierta:
                # Ya está abierta → cerrar
                actuador.cerrar_puerta()
                estado = "CERRADA"
            else:
                # Está cerrada → abrir temporal
                actuador.abrir_puerta_temporal()
                estado = "ABIERTA"
            
            db.insert_event("BOTON", f"Boton 1: Puerta {estado}")
            client.publish(f"{gl.TOPIC_BASE}/actuadores/puerta", estado)
            print(f"[BOTON 1] Puerta {estado}")

        # Boton 2 - Toggle modo luz
        if botones.get('boton2', False):
            actuador.toggle_modo_luz()
            modo_str = "AUTOMATICO" if actuador.modo_luz_auto else "MANUAL"
            client.publish(f"{gl.TOPIC_BASE}/actuadores/luces", f"MODO_{modo_str}", retain=True)
            db.insert_event("BOTON", f"Boton 2: Modo {modo_str}")
            print(f"[BOTON 2] Modo {modo_str}")

        # Boton 3 - Silenciar alarma
        if botones.get('boton3', False):
            actuador.silenciar_alarma()
            db.insert_event("BOTON", "Boton 3: Alarma silenciada")
            client.publish(f"{gl.TOPIC_BASE}/actuadores/alarma", "SILENCIADA", retain=True)
            print("[BOTON 3] Alarma silenciada")

        # Boton 4 - Restablecer alerta
        if botones.get('boton4', False):
            gas_actual = sensor.leer_gas()
            if gas_actual <= gl.UMBRAL_GAS_PELIGRO:
                actuador.desactivar_alarma()
                db.insert_event("BOTON", "Boton 4: Alerta restablecida")
                client.publish(f"{gl.TOPIC_BASE}/actuadores/alarma", "RESTABLECIDA", retain=True)
                print("[BOTON 4] Alerta restablecida")
            else:
                print("[BOTON 4] Gas aun peligroso")
        
        # ==========================================
        # PERSISTENCIA EN MONGODB
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
        # ACTUALIZAR LCD (ROTATIVO, CADA 2s)
        # ==========================================
        if tiempo_actual - ultimo_lcd >= INTERVALO_LCD:
            ultimo_lcd = tiempo_actual
            
            if pantalla_lcd == 0:
                linea1, linea2 = f"Temp:{temp}C", f"Hum:{hum}%"
            elif pantalla_lcd == 1:
                linea1, linea2 = "Gas/Humo:", f"{gas}"
            elif pantalla_lcd == 2:
                linea1, linea2 = "Distancia:", f"{dist}cm"
            elif pantalla_lcd == 3:
                linea1, linea2 = "Nivel de luz:", f"{luz}"
            elif pantalla_lcd == 4:
                linea1, linea2 = "Puerta:", "ABIERTA" if actuador.puerta_abierta else "CERRADA"
            else:
                linea1, linea2 = "Estado:", estado_actual
            
            # Prioridad de alertas (sobrescribe cualquier pantalla)
            if estado_actual == gl.ESTADO_EMERGENCIA:
                linea1, linea2 = "*** EMERGENCIA ***", f"Gas:{gas}"
            elif estado_actual == gl.ESTADO_ADVERTENCIA:
                linea1, linea2 = "*** ADVERTENCIA ***", f"T:{temp}C H:{hum}%"
            
            actuador.actualizar_lcd(linea1, linea2)
            pantalla_lcd = (pantalla_lcd + 1) % PANTALLAS_LCD

        # ==========================================
        # LOGICA DE ESTADOS GLOBALES (SOLO EVENTOS AL CAMBIAR)
        # ==========================================
        nuevo_estado = gl.ESTADO_NORMAL

        # EMERGENCIA
        if gas > gl.UMBRAL_GAS_PELIGRO:
            nuevo_estado = gl.ESTADO_EMERGENCIA
            
            if nuevo_estado != estado_actual:
                actuador.activar_alarma()
                actuador.abrir_puerta()
                try:
                    db.insert_event("EMERGENCIA", f"Gas peligroso: {gas}")
                except Exception as e:
                    print(f"[MONGO] Error al insertar evento: {e}")
                client.publish(f"{gl.TOPIC_BASE}/actuadores/alarma", "ON")
                client.publish(f"{gl.TOPIC_BASE}/actuadores/puerta", "ABIERTA_AUTO", retain=True)
                
        # ADVERTENCIA
        elif temp > gl.UMBRAL_TEMP_ALTA or not (gl.UMBRAL_HUMEDAD_MIN <= hum <= gl.UMBRAL_HUMEDAD_MAX):
            nuevo_estado = gl.ESTADO_ADVERTENCIA
            
            if temp > gl.UMBRAL_TEMP_ALTA:
                actuador.set_modo_ventilador(True)
                actuador.encender_ventilador()
                if ultimo_estado_ventilador_auto != "ON":
                    ultimo_estado_ventilador_auto = "ON"
                    if nuevo_estado != estado_actual:
                        try:
                            db.insert_event("ADVERTENCIA", f"Temp alta: {temp}C")
                        except Exception as e:
                            print(f"[MONGO] Error al insertar evento: {e}")
                    client.publish(f"{gl.TOPIC_BASE}/actuadores/ventilador", "ON", retain=True)
            else:
                if actuador.modo_ventilador_auto:
                    actuador.apagar_ventilador()
                    client.publish(f"{gl.TOPIC_BASE}/actuadores/ventilador", "OFF", retain=True)
            
            if not (gl.UMBRAL_HUMEDAD_MIN <= hum <= gl.UMBRAL_HUMEDAD_MAX) and nuevo_estado != estado_actual:
                try:
                    db.insert_event("ADVERTENCIA", f"Humedad fuera: {hum}%")
                except Exception as e:
                    print(f"[MONGO] Error al insertar evento: {e}")
        
        # NORMAL
        else:
            nuevo_estado = gl.ESTADO_NORMAL
            
            if actuador.modo_ventilador_auto:
                actuador.apagar_ventilador()
                if ultimo_estado_ventilador_auto != "OFF":
                    ultimo_estado_ventilador_auto = "OFF"
                    client.publish(f"{gl.TOPIC_BASE}/actuadores/ventilador", "OFF", retain=True)

        # SALIDA DE EMERGENCIA
        if estado_actual == gl.ESTADO_EMERGENCIA and gas <= gl.UMBRAL_GAS_PELIGRO:
            actuador.desactivar_alarma()
            client.publish(f"{gl.TOPIC_BASE}/actuadores/alarma", "RESTABLECIDA", retain=True)
            try:
                db.insert_event("NORMAL", "Saliendo de EMERGENCIA")
            except Exception as e:
                print(f"[MONGO] Error al insertar evento: {e}")
        
        # CAMBIO DE ESTADO
        if nuevo_estado != estado_actual:
            print(f"[ALERTA] Cambio de estado: {estado_actual} -> {nuevo_estado}")
            db.update_system_status(nuevo_estado)
            try:
                db.insert_event("CAMBIO_ESTADO", f"Estado: {nuevo_estado}")
            except Exception as e:
                print(f"[MONGO] Error al insertar evento: {e}")
            client.publish(f"{gl.TOPIC_BASE}/estado/global", nuevo_estado, retain=True)
            actuador.actualizar_estado(nuevo_estado)
            estado_actual = nuevo_estado

        # CONTROL DE ILUMINACION AUTOMATICA
        if actuador.modo_luz_auto:
            if luz > gl.UMBRAL_LUZ_BAJA:
                actuador.encender_luces()
                estado_luz_auto = "AUTO_ON"
            else:
                actuador.apagar_luces()
                estado_luz_auto = "AUTO_OFF"

            if estado_luz_auto != ultimo_estado_luces_auto:
                ultimo_estado_luces_auto = estado_luz_auto
                client.publish(f"{gl.TOPIC_BASE}/actuadores/luces", estado_luz_auto, retain=True)
        
        # CONTROL DE PUERTA POR DISTANCIA
        if dist < gl.UMBRAL_DISTANCIA_APERTURA and not actuador.puerta_abierta:
            actuador.abrir_puerta_temporal()
            try:
                db.insert_event("PUERTA", f"Apertura por distancia: {dist}cm")
            except Exception as e:
                print(f"[MONGO] Error al insertar evento: {e}")
            client.publish(f"{gl.TOPIC_BASE}/actuadores/puerta", "ABIERTA_AUTO", retain=True)
        
        # ==========================================
        # ARM64
        # ==========================================
        if tiempo_actual - ultimo_arm64 >= INTERVALO_ARM64:
            ultimo_arm64 = tiempo_actual
            sensor.generar_archivo_arm64(20)
            
            try:
                resultado = procesar_arm64()
                max_val = resultado["max"]
                min_val = resultado["min"]
                avg_val = resultado["avg"]
                count_val = resultado["count"]
                
                db.insert_arm64_result(max_val, min_val, avg_val, count_val)
                payload = f"MAX:{max_val},MIN:{min_val},AVG:{avg_val},COUNT:{count_val}"
                client.publish(f"{gl.TOPIC_BASE}/arm64/resultados", payload, retain=True)
                print(f"ARM64     | MAX:{max_val}  MIN:{min_val}  AVG:{avg_val}  COUNT:{count_val}")
                
            except Exception as e:
                print(f"ARM64     | Error: {e}")
        
        # ==========================================
        # PUBLICAR ESTADO DE PUERTA
        # ==========================================
        estado_puerta_actual = "ABIERTA" if actuador.puerta_abierta else "CERRADA"
        if estado_puerta_actual != ultimo_estado_puerta:
            ultimo_estado_puerta = estado_puerta_actual
            client.publish(f"{gl.TOPIC_BASE}/actuadores/puerta", estado_puerta_actual, retain=True)
        
        # ==========================================
        # MOSTRAR CONSOLA
        # ==========================================
        print("\n" + "-"*60)
        print(f"LECTURAS  | Temp:{temp}C  Hum:{hum}%  Gas:{gas}  Dist:{dist}cm  Luz:{luz}")
        print(f"ESTADO    | {estado_actual}  |  Puerta:{'ABIERTA' if actuador.puerta_abierta else 'CERRADA'}  Luces:{'ON' if actuador.luces_encendidas else 'OFF'}")
        print(f"ACTUADORES| Ventilador:{'ON' if actuador.ventilador_encendido else 'OFF'}  Alarma:{'ON' if actuador.alarma_activada else 'OFF'}  Modo:{'AUTO' if actuador.modo_luz_auto else 'MANUAL'}")
        print("-"*60)
        
        # ==========================================
        # PAUSA PARA NO SATURAR CPU
        # ==========================================
        time.sleep(0.01)

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