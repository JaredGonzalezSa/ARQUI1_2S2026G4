import paho.mqtt.client as mqtt

BROKER = "broker.emqx.io"
PORT = 1883
# Usamos el comodín '#' para escuchar absolutamente todo lo que pase en tu edificio
TOPIC = "202500177/edificio/#" 

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Suscrito exitosamente al broker EMQX.")
        client.subscribe(TOPIC)
    else:
        print(f"Error al conectar. Código: {rc}")

def on_message(client, userdata, msg):
    print(f"[NUEVO MENSAJE] Tópico: {msg.topic} | Carga: {msg.payload.decode('utf-8')}")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

print(f"Conectando a {BROKER}...")
client.connect(BROKER, PORT, 60)

# Inicia un ciclo infinito para quedarse escuchando
client.loop_forever()