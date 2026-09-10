# test_leds.py
# Prueba individual de todos los LEDs
# - LEDs de estado: Verde, Amarillo, Rojo
# - LEDs de iluminación: Zona 1, Zona 2, Zona 3
# - LED de puerta (COMENTADO - no conectado)

import time
import RPi.GPIO as GPIO
import globals as gl

# Configurar GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# ==========================================
# DEFINIR TODOS LOS LEDS
# ==========================================
LEDS = {
    "Verde (Estado)": gl.PIN_LED_VERDE,
    "Amarillo (Estado)": gl.PIN_LED_AMARILLO,
    "Rojo (Estado)": gl.PIN_LED_ROJO,
    "Zona 1": gl.PIN_LED_ZONA1,
    "Zona 2": gl.PIN_LED_ZONA2,
    "Zona 3": gl.PIN_LED_ZONA3,
    # "Puerta": gl.PIN_LED_PUERTA,  # COMENTADO: LED de puerta no conectado
}

# Configurar todos como salida
for nombre, pin in LEDS.items():
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, False)  # Apagar al inicio
    print(f"[OK] {nombre} en GPIO{pin}")

print("\n" + "="*50)
print("PRUEBA DE LEDS")
print("="*50)

try:
    while True:
        print("\n" + "-"*40)
        print("1. Encender todos los LEDs")
        print("2. Apagar todos los LEDs")
        print("3. Secuencia de LEDs (uno por uno)")
        print("4. LEDs de estado (Verde -> Amarillo -> Rojo)")
        print("5. LEDs de iluminación (Zona1 -> Zona2 -> Zona3)")
        print("0. Salir")
        print("-"*40)
        
        opcion = input("Selecciona una opción: ").strip()
        
        if opcion == "0":
            break
            
        elif opcion == "1":
            print("\n[ENCENDIENDO TODOS]")
            for nombre, pin in LEDS.items():
                GPIO.output(pin, True)
                print(f"  {nombre} ENCENDIDO")
            time.sleep(0.5)
            
        elif opcion == "2":
            print("\n[APAGANDO TODOS]")
            for nombre, pin in LEDS.items():
                GPIO.output(pin, False)
                print(f"  {nombre} APAGADO")
            time.sleep(0.5)
            
        elif opcion == "3":
            print("\n[SECUENCIA UNO POR UNO]")
            for nombre, pin in LEDS.items():
                print(f"  {nombre} ENCENDIDO")
                GPIO.output(pin, True)
                time.sleep(0.5)
                GPIO.output(pin, False)
                print(f"  {nombre} APAGADO")
                time.sleep(0.2)
                
        elif opcion == "4":
            print("\n[LEDS DE ESTADO]")
            # Verde
            print("  Verde (NORMAL)")
            GPIO.output(gl.PIN_LED_VERDE, True)
            GPIO.output(gl.PIN_LED_AMARILLO, False)
            GPIO.output(gl.PIN_LED_ROJO, False)
            time.sleep(2)
            # Amarillo
            print("  Amarillo (ADVERTENCIA)")
            GPIO.output(gl.PIN_LED_VERDE, False)
            GPIO.output(gl.PIN_LED_AMARILLO, True)
            GPIO.output(gl.PIN_LED_ROJO, False)
            time.sleep(2)
            # Rojo
            print("  Rojo (EMERGENCIA)")
            GPIO.output(gl.PIN_LED_VERDE, False)
            GPIO.output(gl.PIN_LED_AMARILLO, False)
            GPIO.output(gl.PIN_LED_ROJO, True)
            time.sleep(2)
            # Apagar todo
            GPIO.output(gl.PIN_LED_VERDE, False)
            GPIO.output(gl.PIN_LED_AMARILLO, False)
            GPIO.output(gl.PIN_LED_ROJO, False)
            
        elif opcion == "5":
            print("\n[LEDS DE ILUMINACIÓN]")
            # Zona 1
            print("  Zona 1")
            GPIO.output(gl.PIN_LED_ZONA1, True)
            GPIO.output(gl.PIN_LED_ZONA2, False)
            GPIO.output(gl.PIN_LED_ZONA3, False)
            time.sleep(1.5)
            # Zona 2
            print("  Zona 2")
            GPIO.output(gl.PIN_LED_ZONA1, False)
            GPIO.output(gl.PIN_LED_ZONA2, True)
            GPIO.output(gl.PIN_LED_ZONA3, False)
            time.sleep(1.5)
            # Zona 3
            print("  Zona 3")
            GPIO.output(gl.PIN_LED_ZONA1, False)
            GPIO.output(gl.PIN_LED_ZONA2, False)
            GPIO.output(gl.PIN_LED_ZONA3, True)
            time.sleep(1.5)
            # Todas
            print("  Todas las zonas")
            GPIO.output(gl.PIN_LED_ZONA1, True)
            GPIO.output(gl.PIN_LED_ZONA2, True)
            GPIO.output(gl.PIN_LED_ZONA3, True)
            time.sleep(1.5)
            # Apagar todo
            GPIO.output(gl.PIN_LED_ZONA1, False)
            GPIO.output(gl.PIN_LED_ZONA2, False)
            GPIO.output(gl.PIN_LED_ZONA3, False)
            
        else:
            print("\n[ERROR] Opción no válida")

except KeyboardInterrupt:
    print("\n\nPrueba interrumpida por usuario")

finally:
    # Apagar todos los LEDs al salir
    print("\n[LIMPIANDO] Apagando todos los LEDs...")
    for nombre, pin in LEDS.items():
        GPIO.output(pin, False)
    GPIO.cleanup()
    print("[OK] GPIO liberados")