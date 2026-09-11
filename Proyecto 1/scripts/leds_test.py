# test_leds_zona.py
import RPi.GPIO as GPIO
import time
import sys
sys.path.insert(0, '.')
import globals as gl

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

pines = [gl.PIN_LED_ZONA1, gl.PIN_LED_ZONA2, gl.PIN_LED_ZONA3]
nombres = ["ZONA 1", "ZONA 2", "ZONA 3"]

for pin in pines:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, False)

print("Probando LEDs de iluminación...")
for i, pin in enumerate(pines):
    print(f"Encendiendo {nombres[i]} (GPIO{pin})")
    GPIO.output(pin, True)
    time.sleep(1.5)
    GPIO.output(pin, False)
    time.sleep(0.5)

print("Prueba completada")
GPIO.cleanup()