import paho.mqtt.client as mqtt
import time

BROKER = "broker.emqx.io"
PORT = 1883
TOPIC = "202500177/edificio/sensores/temperatura"

client = mqtt.Client()
client.connect(BROKER, PORT, 60)

print(f"Enviando lectura simulada a {TOPIC}...")
# Publicamos un dato simulado de 28 grados
client.publish(TOPIC, "28")
time.sleep(1) # Pequeña pausa para asegurar el envío
print("Mensaje enviado correctamente.")
client.disconnect()