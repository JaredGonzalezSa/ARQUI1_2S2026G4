import time
from Adafruit_DHT import DHT11, Raspberry_Pi

PIN = 5

print("Iniciando lectura directa con el driver de Raspberry Pi... Presiona Ctrl+C para salir.")

try:
    while True:
        humedad, temperatura = Raspberry_Pi.read(DHT11, PIN)

        if humedad is not None and temperatura is not None:
            print(f"Temperatura: {temperatura:.1f}°C  |  Humedad: {humedad:.1f}%")
        else:
            print("⚠️ Error: Falló la comunicación con el DHT11 (Timeout).")

        time.sleep(3.0)

except KeyboardInterrupt:
    print("\nPrograma detenido por el usuario.")