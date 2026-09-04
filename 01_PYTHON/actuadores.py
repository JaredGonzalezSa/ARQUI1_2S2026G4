# Control de actuadores: servo, ventilador, LEDs, buzzer, botones, y LCD vía serial

import time
import threading
import globals as gl

import RPi.GPIO as GPIO
    

class ActuadorManager:
    def __init__(self, serial_conexion=None):
        """
        serial_conexion: objeto serial para comunicarse con Arduino (para LCD)
        """
        print("[ACTUADORES] Inicializando...")
        
        # Pines desde globals
        self.PIN_VENTILADOR = gl.PIN_VENTILADOR
        self.PIN_LED_PUERTA = gl.PIN_LED_PUERTA
        self.PIN_SERVO = gl.PIN_SERVO
        self.PIN_LED_VERDE = gl.PIN_LED_VERDE
        self.PIN_LED_AMARILLO = gl.PIN_LED_AMARILLO
        self.PIN_LED_ROJO = gl.PIN_LED_ROJO
        self.PIN_LED_ZONA1 = gl.PIN_LED_ZONA1
        self.PIN_LED_ZONA2 = gl.PIN_LED_ZONA2
        self.PIN_LED_ZONA3 = gl.PIN_LED_ZONA3
        self.PIN_BUZZER = gl.PIN_BUZZER
        self.PIN_BOTON1 = gl.PIN_BOTON1
        self.PIN_BOTON2 = gl.PIN_BOTON2
        self.PIN_BOTON3 = gl.PIN_BOTON3
        self.PIN_BOTON4 = gl.PIN_BOTON4
        
        # Conexión serial para LCD 
        self.serial_conexion = serial_conexion
        
        # Estado interno
        self.puerta_abierta = False
        self.luces_encendidas = False
        self.ventilador_encendido = False
        self.alarma_activada = False
        self.modo_luz_auto = True
        self.estado_actual_global = gl.ESTADO_NORMAL
        self.timer_puerta = None
        
        # Inicializar GPIO y servo
        self._inicializar_gpio()
        self._inicializar_servo()
        
        # Estado inicial: LEDs de estado apagados, alarma apagada, luces apagadas
        self._actualizar_leds_estado(gl.ESTADO_NORMAL)
        self._set_buzzer(False)
        self._set_luces(False)
        
        # Enviar mensaje inicial al LCD
        self.actualizar_lcd("Sistema Iniciado", "Esperando...")
        
        print("[ACTUADORES] Listo")
    
    def _inicializar_gpio(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        # Salidas
        GPIO.setup(self.PIN_VENTILADOR, GPIO.OUT)
        GPIO.setup(self.PIN_LED_PUERTA, GPIO.OUT)
        GPIO.setup(self.PIN_LED_VERDE, GPIO.OUT)
        GPIO.setup(self.PIN_LED_AMARILLO, GPIO.OUT)
        GPIO.setup(self.PIN_LED_ROJO, GPIO.OUT)
        GPIO.setup(self.PIN_LED_ZONA1, GPIO.OUT)
        GPIO.setup(self.PIN_LED_ZONA2, GPIO.OUT)
        GPIO.setup(self.PIN_LED_ZONA3, GPIO.OUT)
        GPIO.setup(self.PIN_BUZZER, GPIO.OUT)
        # Botones con pull-up (activos en bajo)
        GPIO.setup(self.PIN_BOTON1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.PIN_BOTON2, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.PIN_BOTON3, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.PIN_BOTON4, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        # Apagar todo al inicio
        GPIO.output(self.PIN_VENTILADOR, False)
        GPIO.output(self.PIN_LED_PUERTA, False)
        GPIO.output(self.PIN_LED_VERDE, False)
        GPIO.output(self.PIN_LED_AMARILLO, False)
        GPIO.output(self.PIN_LED_ROJO, False)
        GPIO.output(self.PIN_LED_ZONA1, False)
        GPIO.output(self.PIN_LED_ZONA2, False)
        GPIO.output(self.PIN_LED_ZONA3, False)
        GPIO.output(self.PIN_BUZZER, False)
    
    def _inicializar_servo(self):
        GPIO.setup(self.PIN_SERVO, GPIO.OUT)
        self.servo_pwm = GPIO.PWM(self.PIN_SERVO, 50)
        self.servo_pwm.start(0)
        self.servo_pwm.ChangeDutyCycle(2.5)  # cerrado
        time.sleep(0.5)
        self.servo_pwm.ChangeDutyCycle(0)
    
    # ---------- COMANDOS PARA ARDUINO (LCD) ----------
    def actualizar_lcd(self, linea1, linea2):
        """
        Envía texto al LCD a través de Arduino por serial.
        Formato: "LCD:linea1,linea2"
        """
        if not self.serial_conexion or not self.serial_conexion.is_open:
            return
        try:
            # Recortar a 16 caracteres
            linea1 = linea1[:16].ljust(16)
            linea2 = linea2[:16].ljust(16)
            mensaje = f"LCD:{linea1},{linea2}\n"
            self.serial_conexion.write(mensaje.encode())
        except Exception as e:
            print(f"[LCD] Error enviando: {e}")
    
    # ---------- LEDS DE ILUMINACIÓN (3 zonas) ----------
    def _set_luces(self, estado):
        """Enciende o apaga los 3 LEDs de iluminación simultáneamente"""
        GPIO.output(self.PIN_LED_ZONA1, estado)
        GPIO.output(self.PIN_LED_ZONA2, estado)
        GPIO.output(self.PIN_LED_ZONA3, estado)
        self.luces_encendidas = estado
    
    def encender_luces(self):
        self._set_luces(True)
        return True
    
    def apagar_luces(self):
        self._set_luces(False)
        return True
    
    def toggle_luces(self):
        if self.luces_encendidas:
            return self.apagar_luces()
        else:
            return self.encender_luces()
    
    def set_modo_luz(self, auto=True):
        self.modo_luz_auto = auto
        return True
    
    def toggle_modo_luz(self):
        self.modo_luz_auto = not self.modo_luz_auto
        return self.modo_luz_auto
    
    # ---------- LEDS DE ESTADO (verde, amarillo, rojo) ----------
    def _actualizar_leds_estado(self, estado):
        verde = (estado == gl.ESTADO_NORMAL)
        amarillo = (estado == gl.ESTADO_ADVERTENCIA)
        rojo = (estado == gl.ESTADO_EMERGENCIA)
        GPIO.output(self.PIN_LED_VERDE, verde)
        GPIO.output(self.PIN_LED_AMARILLO, amarillo)
        GPIO.output(self.PIN_LED_ROJO, rojo)
    
    # ---------- BUZZER ----------
    def _set_buzzer(self, estado):
        GPIO.output(self.PIN_BUZZER, estado)
    
    def activar_alarma(self):
        self._set_buzzer(True)
        self.alarma_activada = True
        return True
    
    def desactivar_alarma(self):
        self._set_buzzer(False)
        self.alarma_activada = False
        return True
    
    def toggle_alarma(self):
        if self.alarma_activada:
            return self.desactivar_alarma()
        else:
            return self.activar_alarma()
    
    # ---------- VENTILADOR ----------
    def encender_ventilador(self):
        GPIO.output(self.PIN_VENTILADOR, True)
        self.ventilador_encendido = True
        return True
    
    def apagar_ventilador(self):
        GPIO.output(self.PIN_VENTILADOR, False)
        self.ventilador_encendido = False
        return True
    
    def toggle_ventilador(self):
        if self.ventilador_encendido:
            return self.apagar_ventilador()
        else:
            return self.encender_ventilador()
    
    # ---------- PUERTA (servo) ----------
    def abrir_puerta(self):
        self.servo_pwm.ChangeDutyCycle(7.5)
        time.sleep(0.5)
        self.servo_pwm.ChangeDutyCycle(0)
        GPIO.output(self.PIN_LED_PUERTA, True)
        self.puerta_abierta = True
        self._cancelar_timer_puerta()
        return True
    
    def cerrar_puerta(self):
        self.servo_pwm.ChangeDutyCycle(2.5)
        time.sleep(0.5)
        self.servo_pwm.ChangeDutyCycle(0)
        GPIO.output(self.PIN_LED_PUERTA, False)
        self.puerta_abierta = False
        self._cancelar_timer_puerta()
        return True
    
    def _cancelar_timer_puerta(self):
        if self.timer_puerta:
            self.timer_puerta.cancel()
            self.timer_puerta = None
    
    def _cerrar_puerta_auto(self):
        self.cerrar_puerta()
    
    def abrir_puerta_temporal(self, tiempo=gl.TIEMPO_PUERTA_ABIERTA):
        self.abrir_puerta()
        self._cancelar_timer_puerta()
        self.timer_puerta = threading.Timer(tiempo, self._cerrar_puerta_auto)
        self.timer_puerta.daemon = True
        self.timer_puerta.start()
        return True
    
    def toggle_puerta(self):
        if self.puerta_abierta:
            return self.cerrar_puerta()
        else:
            return self.abrir_puerta()
    
    # ---------- ESTADO GLOBAL ----------
    def actualizar_estado(self, estado):
        """Actualiza LEDs de estado y alarma según el estado global"""
        self.estado_actual_global = estado
        self._actualizar_leds_estado(estado)
        if estado == gl.ESTADO_EMERGENCIA:
            self.activar_alarma()
        # Si sale de emergencia, no desactivamos alarma automáticamente
    
    # ---------- LECTURA DE BOTONES ----------
    def leer_botones(self):
        """
        Retorna diccionario con estado de cada botón (True = presionado).
        Los botones están con pull-up, así que 0 = presionado.
        """
        return {
            'boton1': GPIO.input(self.PIN_BOTON1) == 0,
            'boton2': GPIO.input(self.PIN_BOTON2) == 0,
            'boton3': GPIO.input(self.PIN_BOTON3) == 0,
            'boton4': GPIO.input(self.PIN_BOTON4) == 0
        }
    
    # ---------- ESTADO PARA DASHBOARD ----------
    def obtener_estados(self):
        return {
            'puerta': 'ABIERTA' if self.puerta_abierta else 'CERRADA',
            'luces': 'ENCENDIDAS' if self.luces_encendidas else 'APAGADAS',
            'modo_luz': 'AUTOMÁTICO' if self.modo_luz_auto else 'MANUAL',
            'ventilador': 'ENCENDIDO' if self.ventilador_encendido else 'APAGADO',
            'alarma': 'ACTIVADA' if self.alarma_activada else 'DESACTIVADA'
        }
    
    def __del__(self):
        try:
            if hasattr(self, 'servo_pwm'):
                self.servo_pwm.stop()
        except:
            pass
        GPIO.cleanup()