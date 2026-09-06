import time
import subprocess
import os
import paho.mqtt.client as mqtt
import globals as gl
from mongo import MongoDBManager
from sensores import SensorManager
from actuadores import ActuadorManager

db = MongoDBManager()
sensor = SensorManager()
actuador = ActuadorManager()

estado_actual = gl.ESTADO_NORMAL
actuador.actualizar_estado(estado_actual)

contador_ciclos = 0
CICLOS_PARA_MONGODB = 6

ultimo_boton = {'boton1': 0, 'boton2': 0, 'boton3': 0, 'boton4': 0}
DEBOUNCE_MS = 300

ultimo_cambio_lcd = 0
indice_pantalla = 0

PANTALLAS = [
    ("Temp/Hum", "T:{temp}C H:{hum}%"),
    ("Gas/Luz", "G:{gas} L:{luz}"),
    ("Puerta/Dist", "D:{dist}cm P:{puerta}"),
    ("Estado/Modo", "S:{estado} M:{modo}")
]


def imprimir_sensores(temp, hum, gas, dist, luz):
    os.system('clear')
    print("=" * 50)
    print("SISTEMA EDIFICIO INTELIGENTE")
    print("=" * 50)
    print(f"Fecha: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 50)
    print(f"Temperatura:  {temp} C")
    print(f"Humedad:      {hum} %")
    print(f"Gas (MQ-2):   {gas}")
    print(f"Distancia:    {dist} cm")
    print(f"Luz (LDR):    {luz}")
    print("-" * 50)
    print(f"Estado:       {estado_actual}")
    print(f"Puerta:       {'ABIERTA' if actuador.puerta_abierta else 'CERRADA'}")
    print(f"Luces:        {'ENCENDIDAS' if actuador.luces_encendidas else 'APAGADAS'}")
    print(f"Ventilador:   {'ENCENDIDO' if actuador.ventilador_encendido else 'APAGADO'}")
    print(f"Alarma:       {'ACTIVADA' if actuador.alarma_activada else 'DESACTIVADA'}")
    print(f"Modo Luz:     {'AUTOMATICO' if actuador.modo_luz_auto else 'MANUAL'}")
    print("-" * 50)
    

def actualizar_lcd_rotativo():
    global ultimo_cambio_lcd, indice_pantalla
    
    ahora = time.time()
    if ahora - ultimo_cambio_lcd >= gl.TIEMPO_ROTACION_LCD:
        ultimo_cambio_lcd = ahora
        indice_pantalla = (indice_pantalla + 1) % len(PANTALLAS)
    
    temp = sensor.ultimos_valores['temperatura']
    hum = sensor.ultimos_valores['humedad']
    gas = sensor.ultimos_valores['gas']
    luz = sensor.ultimos_valores['luz']
    dist = sensor.ultimos_valores['distancia']
    puerta = "ABI" if actuador.puerta_abierta else "CER"
    estado = estado_actual[:4]
    modo = "AUTO" if actuador.modo_luz_auto else "MAN"
    
    if indice_pantalla == 0:
        linea1 = f"T:{temp}C H:{hum}%"
        linea2 = "Temp/Hum"
    elif indice_pantalla == 1:
        linea1 = f"G:{gas} L:{luz}"
        linea2 = "Gas/Luz"
    elif indice_pantalla == 2:
        linea1 = f"D:{dist}cm P:{puerta}"
        linea2 = "Dist/Puerta"
    else:
        linea1 = f"S:{estado} M:{modo}"
        linea2 = "Estado/Modo"
    
    actuador.actualizar_lcd(linea1, linea2)


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("[MQTT] Conectado a EMQX.")
        client.subscribe(f"{gl.TOPIC_BASE}/control/remoto")
    else:
        print(f"[MQTT] Error: {reason_code}")


def on_message(client, userdata, msg):
    comando = msg.payload.decode('utf-8')
    print(f"[COMANDO] {comando}")
    db.col_commands.insert_one({"comando": comando, "timestamp": db.get_timestamp()})
    
    if comando == "ABRIR_PUERTA":
        actuador.abrir_puerta_temporal()
        db.insert_event("COMANDO", "Puerta abierta remotamente")
    elif comando == "CERRAR_PUERTA":
        actuador.cerrar_puerta()
        db.insert_event("COMANDO", "Puerta cerrada remotamente")
    elif comando == "TOGGLE_PUERTA":
        actuador.toggle_puerta()
        db.insert_event("COMANDO", "Puerta toggled remotamente")
    elif comando == "ENCENDER_LUCES":
        actuador.encender_luces()
        db.insert_event("COMANDO", "Luces ON remotamente")
    elif comando == "APAGAR_LUCES":
        actuador.apagar_luces()
        db.insert_event("COMANDO", "Luces OFF remotamente")
    elif comando == "TOGGLE_LUCES":
        actuador.toggle_luces()
        db.insert_event("COMANDO", "Luces toggled remotamente")
    elif comando == "MODO_AUTO":
        actuador.set_modo_luz(True)
        db.insert_event("COMANDO", "Modo AUTO")
    elif comando == "MODO_MANUAL":
        actuador.set_modo_luz(False)
        db.insert_event("COMANDO", "Modo MANUAL")
    elif comando == "SILENCIAR_ALARMA":
        actuador.desactivar_alarma()
        db.insert_event("COMANDO", "Alarma silenciada")
    elif comando == "RESTABLECER_ALERTA":
        if sensor.leer_gas() <= gl.UMBRAL_GAS_PELIGRO:
            actuador.desactivar_alarma()
            db.insert_event("COMANDO", "Alerta restablecida")
    elif comando == "TOGGLE_VENTILADOR":
        actuador.toggle_ventilador()
        db.insert_event("COMANDO", "Ventilador toggled")


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"Backend_{gl.CARNE}")
client.on_connect = on_connect
client.on_message = on_message
client.connect(gl.BROKER, gl.PORT, 60)
client.loop_start()


try:
    print("\n" + "="*50)
    print("SISTEMA EDIFICIO INTELIGENTE")
    print("="*50)
    
    db.update_system_status(estado_actual)
    
    while True:
        
        temp = sensor.leer_temperatura()
        hum = sensor.leer_humedad()
        gas = sensor.leer_gas()
        dist = sensor.leer_distancia()
        luz = sensor.leer_luz()
        
        imprimir_sensores(temp, hum, gas, dist, luz)
        
        client.publish(f"{gl.TOPIC_BASE}/sensores/temperatura", temp)
        client.publish(f"{gl.TOPIC_BASE}/sensores/humedad", hum)
        client.publish(f"{gl.TOPIC_BASE}/sensores/gas", gas)
        client.publish(f"{gl.TOPIC_BASE}/sensores/distancia", dist)
        client.publish(f"{gl.TOPIC_BASE}/sensores/luz", luz)
        
        contador_ciclos += 1
        if contador_ciclos >= CICLOS_PARA_MONGODB:
            db.insert_sensor_reading("temperatura", temp)
            db.insert_sensor_reading("humedad", hum)
            db.insert_sensor_reading("gas", gas)
            db.insert_sensor_reading("distancia", dist)
            db.insert_sensor_reading("luz", luz)
            contador_ciclos = 0
        
        nuevo_estado = gl.ESTADO_NORMAL
        
        if gas > gl.UMBRAL_GAS_PELIGRO:
            nuevo_estado = gl.ESTADO_EMERGENCIA
            actuador.activar_alarma()
            actuador.abrir_puerta_temporal()
            db.insert_event("EMERGENCIA", f"Gas peligroso: {gas}")
            client.publish(f"{gl.TOPIC_BASE}/actuadores/alarma", "ON")
            client.publish(f"{gl.TOPIC_BASE}/actuadores/puerta", "ABIERTA_AUTO")
        
        elif temp > gl.UMBRAL_TEMP_ALTA or not (gl.UMBRAL_HUMEDAD_MIN <= hum <= gl.UMBRAL_HUMEDAD_MAX):
            nuevo_estado = gl.ESTADO_ADVERTENCIA
            
            if temp > gl.UMBRAL_TEMP_ALTA:
                actuador.encender_ventilador()
                db.insert_event("ADVERTENCIA", f"Temp alta: {temp}C")
                client.publish(f"{gl.TOPIC_BASE}/actuadores/ventilador", "ON")
            else:
                actuador.apagar_ventilador()
                client.publish(f"{gl.TOPIC_BASE}/actuadores/ventilador", "OFF")
                
            if not (gl.UMBRAL_HUMEDAD_MIN <= hum <= gl.UMBRAL_HUMEDAD_MAX):
                db.insert_event("ADVERTENCIA", f"Humedad fuera: {hum}%")
        
        else:
            actuador.apagar_ventilador()
            client.publish(f"{gl.TOPIC_BASE}/actuadores/ventilador", "OFF")
            
            if estado_actual == gl.ESTADO_EMERGENCIA and gas <= gl.UMBRAL_GAS_PELIGRO:
                actuador.desactivar_alarma()
                client.publish(f"{gl.TOPIC_BASE}/actuadores/alarma", "OFF")
                db.insert_event("NORMAL", "Saliendo de EMERGENCIA")
        
        if nuevo_estado != estado_actual:
            print(f"Cambio de estado: {estado_actual} -> {nuevo_estado}")
            db.update_system_status(nuevo_estado)
            db.insert_event("CAMBIO_ESTADO", f"Estado: {nuevo_estado}")
            client.publish(f"{gl.TOPIC_BASE}/estado/global", nuevo_estado)
            actuador.actualizar_estado(nuevo_estado)
            estado_actual = nuevo_estado
        
        # Control de iluminacion - Logica correcta
        # Valor ALTO = oscuridad, valor BAJO = iluminado
        if actuador.modo_luz_auto:
            if luz > gl.UMBRAL_LUZ_BAJA:
                actuador.encender_luces()
                client.publish(f"{gl.TOPIC_BASE}/actuadores/luces", "AUTO_ON")
                print(f"Luz oscura ({luz}) -> Luces ON")
            else:
                actuador.apagar_luces()
                client.publish(f"{gl.TOPIC_BASE}/actuadores/luces", "AUTO_OFF")
                print(f"Luz suficiente ({luz}) -> Luces OFF")
        
        if dist < gl.UMBRAL_DISTANCIA_APERTURA and not actuador.puerta_abierta:
            actuador.abrir_puerta_temporal()
            db.insert_event("PUERTA", f"Apertura por distancia: {dist}cm")
            client.publish(f"{gl.TOPIC_BASE}/actuadores/puerta", "ABIERTA_AUTO")
        
        # Botones - Lectura y procesamiento (VERSIÓN CORREGIDA)
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
            actuador.desactivar_alarma()
            db.insert_event("BOTON", "Botón 3: Alarma silenciada")
            client.publish(f"{gl.TOPIC_BASE}/actuadores/alarma", "SILENCIADA")
            ultimo_boton['boton3'] = t_actual_ms

        # Botón 4 - Restablecer alerta
        if botones.get('boton4', False) and (t_actual_ms - ultimo_boton['boton4'] > DEBOUNCE_MS):
            if sensor.leer_gas() <= gl.UMBRAL_GAS_PELIGRO:
                actuador.desactivar_alarma()
                db.insert_event("BOTON", "Botón 4: Alerta restablecida")
                client.publish(f"{gl.TOPIC_BASE}/actuadores/alarma", "RESTABLECIDA")
            ultimo_boton['boton4'] = t_actual_ms
        
         
        actualizar_lcd_rotativo()
        
        sensor.generar_archivo_arm64(20)
        
        try:
            if os.path.exists(gl.ARM64_BIN_PATH):
                subprocess.run([gl.ARM64_BIN_PATH], cwd=".", capture_output=True, text=True, timeout=5)
        except:
            pass
        
        try:
            with open("resultado.txt", "r", encoding="utf-8") as f:
                lineas = f.readlines()
            
            max_val = int(lineas[0].split("=")[1].strip())
            min_val = int(lineas[1].split("=")[1].strip())
            avg_val = int(lineas[2].split("=")[1].strip())
            count_val = int(lineas[3].split("=")[1].strip())
            
            db.insert_arm64_result(max_val, min_val, avg_val, count_val)
            payload = f"MAX:{max_val},MIN:{min_val},AVG:{avg_val},COUNT:{count_val}"
            client.publish(f"{gl.TOPIC_BASE}/arm64/resultados", payload)
        except:
            pass

except KeyboardInterrupt:
    print("\nApagando sistema...")
    client.loop_stop()
    client.disconnect()
finally:
    if 'actuador' in locals():
        del actuador
    if 'sensor' in locals():
        del sensor
    print("Sistema finalizado.")