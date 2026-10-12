"""
Test AISLADO del servo SG90 (Control manual por ángulos en grados).
"""

import RPi.GPIO as GPIO
import time

# ==========================================
# CONFIGURACIÓN
# ==========================================

PIN_SERVO = 18          # GPIO18 (pin físico 12)
FRECUENCIA = 50         # 50 Hz estándar para servos

# Mapeo para SG90 (Ajustable si tu servo requiere calibración)
DUTY_0_GRADOS = 2.5     # ~0°
DUTY_180_GRADOS = 12.5  # ~180°

def grados_a_duty(angulo):
    """Convierte un ángulo en grados (0 a 180) al Duty Cycle correspondiente."""
    return DUTY_0_GRADOS + (angulo / 180.0) * (DUTY_180_GRADOS - DUTY_0_GRADOS)

# ==========================================
# INICIALIZACIÓN
# ==========================================

print("=" * 50)
print("TEST MANUAL DEL SERVO SG90 (EN GRADOS)")
print("=" * 50)
print(f"Pin: GPIO{PIN_SERVO}")
print(f"Frecuencia: {FRECUENCIA} Hz")
print("Ingresa un ángulo entre 0° y 180°.")
print("Escribe -1 para salir.")
print("=" * 50)

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(PIN_SERVO, GPIO.OUT)

servo = GPIO.PWM(PIN_SERVO, FRECUENCIA)
servo.start(grados_a_duty(0))
print(f"[INIT] Servo iniciado a 0° (Duty: {grados_a_duty(0):.2f}%)")

# ==========================================
# BUCLE INTERACTIVO
# ==========================================

try:
    while True:
        entrada = input("\nIngresa el ángulo deseado en grados (0 a 180, o -1 para salir): ").strip()
        
        try:
            angulo = float(entrada)
        except ValueError:
            print("Por favor, ingresa un número entero o decimal válido.")
            continue

        if angulo == -1:
            print("[INFO] Saliendo...")
            break

        if angulo < 0 or angulo > 180:
            print("[ADVERTENCIA] El ángulo debe estar en el rango de 0 a 180 grados.")
            continue

        duty_calculado = grados_a_duty(angulo)
        servo.ChangeDutyCycle(duty_calculado)
        print(f"[MOVE] Posicionando a {angulo:.1f}° (Duty Cycle: {duty_calculado:.2f}%)")

except KeyboardInterrupt:
    print("\n[EXIT] Interrumpido por el usuario (Ctrl+C)")

finally:
    print("[EXIT] Deteniendo PWM y liberando GPIO...")
    servo.stop()
    GPIO.cleanup()
    print("[EXIT] Test terminado.")