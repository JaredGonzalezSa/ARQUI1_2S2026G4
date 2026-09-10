import RPi.GPIO as GPIO
import time

PIN_BUZZER = 26

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(PIN_BUZZER, GPIO.OUT)

print("Probando buzzer con transistor...")
print("Encendiendo por 2 segundos")
GPIO.output(PIN_BUZZER, True)
time.sleep(1)
GPIO.output(PIN_BUZZER, False)
print("Apagado")

GPIO.cleanup()