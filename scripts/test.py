# test_botones.py
import time
import RPi.GPIO as GPIO

# Configuración de pines
BOTONES = {
    1: 22,
    2: 23,
    3: 24,
    4: 25
}

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Configurar como entradas con pull-up
for nombre, pin in BOTONES.items():
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    print(f"Botón {nombre} en GPIO{pin}")

print("\nPresiona los botones (Ctrl+C para salir)")
try:
    while True:
        for nombre, pin in BOTONES.items():
            if GPIO.input(pin) == 0:  # 0 = presionado (pull-up)
                print(f"Botón {nombre} presionado!")
                time.sleep(0.2)  # Anti-rebote
        time.sleep(0.05)
except KeyboardInterrupt:
    print("\nSaliendo...")
finally:
    GPIO.cleanup()