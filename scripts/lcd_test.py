# test_lcd_escribir.py
# Escribe en la consola y el texto se muestra en el LCD

import time
import serial
import globals as gl

PUERTO_SERIAL = gl.PUERTO_SERIAL
BAUDRATE = 9600

def enviar_lcd(ser, linea1, linea2, columnas=16):
    linea1 = linea1[:columnas].ljust(columnas)
    linea2 = linea2[:columnas].ljust(columnas)
    mensaje = f"LCD:{linea1},{linea2}\n"
    ser.write(mensaje.encode('utf-8'))
    print(f"[LCD] {linea1} | {linea2}")

print("="*50)
print("ESCRIBE EN CONSOLA Y SE MUESTRA EN EL LCD")
print("="*50)

try:
    print(f"\nConectando a {PUERTO_SERIAL}...")
    ser = serial.Serial(PUERTO_SERIAL, BAUDRATE, timeout=1)
    time.sleep(2)
    print("[OK] Conexión establecida\n")
    
    print("Escribe lo que quieras mostrar en el LCD")
    print("Línea 1 y Línea 2 (máx 16 caracteres cada una)")
    print("Escribe 'salir' para terminar\n")
    
    while True:
        linea1 = input("Línea 1: ").strip()
        if linea1.lower() == "salir":
            break
        
        linea2 = input("Línea 2: ").strip()
        if linea2.lower() == "salir":
            break
        
        enviar_lcd(ser, linea1, linea2)
        print()

except serial.SerialException as e:
    print(f"\n[ERROR] No se pudo conectar al puerto {PUERTO_SERIAL}")
    print("Verifica que el Arduino esté conectado")
    
except Exception as e:
    print(f"\n[ERROR] {e}")

finally:
    if 'ser' in locals() and ser.is_open:
        ser.close()
        print("\n[OK] Puerto serial cerrado")