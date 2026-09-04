import time
import serial
import threading
import globals as gl

import RPi.GPIO as GPIO
import Adafruit_DHT

class SensorManager:
    def __init__(self, puerto_serial=None):
        print("[SENSORES] Inicializando...")
        
        self.PIN_DHT = gl.PIN_DHT
        self.PIN_TRIG = gl.PIN_TRIG
        self.PIN_ECHO = gl.PIN_ECHO
        
        self.puerto_serial = puerto_serial
        self.serial_conexion = None
        self.datos_arduino = {'gas': 0, 'luz': 0}
        
        self.tiempos_lectura = {
            'temperatura': 3,
            'humedad': 3,
            'gas': 2,
            'distancia': 2,
            'luz': 2
        }
        self.ultimos_valores = {
            'temperatura': 25,
            'humedad': 50,
            'gas': 150,
            'distancia': 30,
            'luz': 500
        }
        self.ultima_lectura = {k: 0 for k in self.ultimos_valores}
        
        self._inicializar_gpio()
        if puerto_serial:
            self._conectar_serial()
        
        self.serial_thread_activo = True
        self.hilo_serial = threading.Thread(target=self._leer_serial_continuo)
        self.hilo_serial.daemon = True
        self.hilo_serial.start()
        print("[SENSORES] Listo")
    
    def _inicializar_gpio(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.PIN_TRIG, GPIO.OUT)
        GPIO.setup(self.PIN_ECHO, GPIO.IN)
        GPIO.output(self.PIN_TRIG, False)
    
    def _conectar_serial(self):
        try:
            self.serial_conexion = serial.Serial(self.puerto_serial, 9600, timeout=0.1)
            time.sleep(2)
            print(f"[SENSORES] Serial conectado en {self.puerto_serial}")
        except Exception as e:
            print(f"[SENSORES] Error serial: {e}")
            self.serial_conexion = None
    
    def _leer_serial_continuo(self):
        while self.serial_thread_activo:
            if self.serial_conexion and self.serial_conexion.is_open:
                try:
                    if self.serial_conexion.in_waiting > 0:
                        linea = self.serial_conexion.readline().decode().strip()
                        if linea:
                            self._procesar_datos_serial(linea)
                except:
                    time.sleep(1)
            else:
                time.sleep(0.5)
            time.sleep(0.01)
    
    def _procesar_datos_serial(self, linea):
        try:
            for item in linea.split(','):
                if ':' in item:
                    clave, valor = item.split(':')
                    clave = clave.strip().upper()
                    if clave == 'GAS':
                        self.datos_arduino['gas'] = int(valor)
                        self.ultimos_valores['gas'] = int(valor)
                        self.ultima_lectura['gas'] = time.time()
                    elif clave == 'LUZ':
                        self.datos_arduino['luz'] = int(valor)
                        self.ultimos_valores['luz'] = int(valor)
                        self.ultima_lectura['luz'] = time.time()
        except:
            pass
    
    def _debe_leer(self, sensor):
        return (time.time() - self.ultima_lectura.get(sensor, 0)) >= self.tiempos_lectura.get(sensor, 3)
    
    def leer_temperatura(self):
        if not self._debe_leer('temperatura'):
            return self.ultimos_valores['temperatura']
        try:
            h, t = Adafruit_DHT.read_retry(Adafruit_DHT.DHT11, self.PIN_DHT)
            if t is not None:
                val = int(round(t))
                self.ultimos_valores['temperatura'] = val
                self.ultima_lectura['temperatura'] = time.time()
                return val
        except:
            pass
        return self.ultimos_valores['temperatura']
    
    def leer_humedad(self):
        if not self._debe_leer('humedad'):
            return self.ultimos_valores['humedad']
        try:
            h, t = Adafruit_DHT.read_retry(Adafruit_DHT.DHT11, self.PIN_DHT)
            if h is not None:
                val = int(round(h))
                self.ultimos_valores['humedad'] = val
                self.ultima_lectura['humedad'] = time.time()
                return val
        except:
            pass
        return self.ultimos_valores['humedad']
    
    def leer_gas(self):
        if not self._debe_leer('gas'):
            return self.ultimos_valores['gas']
        self.ultima_lectura['gas'] = time.time()
        return self.ultimos_valores['gas']
    
    def leer_luz(self):
        if not self._debe_leer('luz'):
            return self.ultimos_valores['luz']
        self.ultima_lectura['luz'] = time.time()
        return self.ultimos_valores['luz']
    
    def leer_distancia(self):
        if not self._debe_leer('distancia'):
            return self.ultimos_valores['distancia']
        try:
            GPIO.output(self.PIN_TRIG, False)
            time.sleep(0.1)
            GPIO.output(self.PIN_TRIG, True)
            time.sleep(0.00001)
            GPIO.output(self.PIN_TRIG, False)
            pulse_start = time.time()
            pulse_end = time.time()
            timeout = 0.1
            start = time.time()
            while GPIO.input(self.PIN_ECHO) == 0:
                pulse_start = time.time()
                if time.time() - start > timeout:
                    return self.ultimos_valores['distancia']
            while GPIO.input(self.PIN_ECHO) == 1:
                pulse_end = time.time()
                if time.time() - start > timeout:
                    return self.ultimos_valores['distancia']
            duration = pulse_end - pulse_start
            dist = int(round(duration * 17150))
            if 2 <= dist <= 400:
                self.ultimos_valores['distancia'] = dist
                self.ultima_lectura['distancia'] = time.time()
                return dist
        except:
            pass
        return self.ultimos_valores['distancia']
    
    def leer_todos(self):
        return {
            'temperatura': self.leer_temperatura(),
            'humedad': self.leer_humedad(),
            'gas': self.leer_gas(),
            'distancia': self.leer_distancia(),
            'luz': self.leer_luz()
        }
    
    def generar_archivo_arm64(self, cantidad=20):
        ruta = "datos.txt"
        lecturas = []
        try:
            with open(ruta, "w") as f:
                for i in range(cantidad):
                    temp = self.leer_temperatura()
                    f.write(f"{temp}\n")
                    lecturas.append(temp)
                    if i < cantidad - 1:
                        time.sleep(0.05)
                f.write("$\n")
            print(f"[ARM64] datos.txt generado con {cantidad} lecturas")
            return lecturas
        except Exception as e:
            print(f"[ARM64] Error: {e}")
            return None
    
    def __del__(self):
        self.serial_thread_activo = False
        if self.serial_conexion and self.serial_conexion.is_open:
            try: self.serial_conexion.close()
            except: pass
        GPIO.cleanup()