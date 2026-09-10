import paho.mqtt.client as mqtt
import time

BROKER = "broker.emqx.io"
BASE = "202500177/edificio"

TOPICS = [
    f"{BASE}/sensores/temperatura",
    f"{BASE}/sensores/humedad",
    f"{BASE}/sensores/gas",
    f"{BASE}/sensores/distancia",
    f"{BASE}/sensores/luz",
    f"{BASE}/actuadores/puerta",
    f"{BASE}/actuadores/luces",
    f"{BASE}/actuadores/ventilador",
    f"{BASE}/actuadores/alarma",
    f"{BASE}/estado/global",
    f"{BASE}/arm64/resultados",
]

cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="limpiar_todo")

def al_conectar(client, userdata, flags, rc, properties):
    if rc == 0:
        print("Conectado. Limpiando TODOS los retains...")
        for topic in TOPICS:
            client.publish(topic, "", retain=True)
            print(f"  Limpiado: {topic}")
        time.sleep(1.5)
        client.disconnect()

cliente.on_connect = al_conectar
cliente.connect(BROKER, 1883, 60)
cliente.loop_forever()