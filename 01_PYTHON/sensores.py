import random
import os

class SensorManager:
    def __init__(self):
        """
        Inicializa los sensores. 
        (Aquí en el futuro importaremos RPi.GPIO y Adafruit_DHT)
        """
        print("[SENSORES] Iniciando sistema de sensores (Modo Simulación Windows)...")

    def leer_temperatura(self):
        # Simula temperatura entre 20 y 35 grados (entero para ARM64)
        return random.randint(20, 35)

    def leer_humedad(self):
        # Simula humedad entre 30% y 80%
        return random.randint(30, 80)

    def leer_gas(self):
        # Simula valor de gas (MQ-2). Normal < 400.
        return random.randint(100, 500)

    def leer_distancia(self):
        # Simula distancia en cm (HC-SR04).
        return random.randint(5, 50)

    def leer_luz(self):
        # Simula nivel de luz (LDR).
        return random.randint(100, 900)

    def generar_archivo_arm64(self, cantidad_lecturas=20):
        """
        Genera el archivo datos.txt estricto para el módulo ARM64.
        Requiere enteros separados por salto de línea y '$' al final.
        """
        ruta_archivo = "datos.txt"
        lecturas = []
        
        try:
            with open(ruta_archivo, "w") as archivo:
                for _ in range(cantidad_lecturas):
                    # El cálculo de máximo, mínimo y promedio lo hará ARM64, no Python
                    temp = self.leer_temperatura()
                    archivo.write(f"{temp}\n")
                    lecturas.append(temp)
                
                # Finalizador estricto exigido por la rúbrica
                archivo.write("$\n")
                
            print(f"[ARM64] Archivo {ruta_archivo} generado con éxito ({cantidad_lecturas} lecturas).")
            return lecturas
        except Exception as e:
            print(f"[ARM64] Error generando el archivo: {e}")
            return None

# Bloque de comprobación aislado
if __name__ == "__main__":
    sensores = SensorManager()
    print(f"Temperatura actual: {sensores.leer_temperatura()} °C")
    print(f"Humedad actual: {sensores.leer_humedad()} %")
    
    # Generar el archivo para el compañero de Ensamblador
    sensores.generar_archivo_arm64()