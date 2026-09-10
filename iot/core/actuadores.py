import time
import threading
import globals as gl
import RPi.GPIO as GPIO

try:
    from rpi_lcd import LCD
    LCD_DISPONIBLE = True
except ImportError:
    LCD_DISPONIBLE = False


class ActuadorManager:
    def __init__(self):
        print("[ACTUADORES] Inicializando...")
        
        self.PIN_LED_PUERTA = gl.PIN_LED_PUERTA
        self.PIN_SERVO = gl.PIN_SERVO
        self.PIN_LED_VERDE = gl.PIN_LED_VERDE
        self.PIN_LED_AMARILLO = gl.PIN_LED_AMARILLO
        self.PIN_LED_ROJO = gl.PIN_LED_ROJO
        self.PIN_LED_ZONA1 = gl.PIN_LED_ZONA1
        self.PIN_LED_ZONA2 = gl.PIN_LED_ZONA2
        self.PIN_LED_ZONA3 = gl.PIN_LED_ZONA3
        self.PIN_LED_VENTILADOR = gl.PIN_LED_VENTILADOR  
        self.PIN_RELAY = gl.PIN_RELAY                   
        self.PIN_BUZZER = gl.PIN_BUZZER
        self.PIN_BOTON1 = gl.PIN_BOTON1
        self.PIN_BOTON2 = gl.PIN_BOTON2
        self.PIN_BOTON3 = gl.PIN_BOTON3
        self.PIN_BOTON4 = gl.PIN_BOTON4
        
        self.lcd = None
        self.lcd_disponible = False
        self._inicializar_lcd()
        
        self.puerta_abierta = False
        self.luces_encendidas = False
        self.ventilador_encendido = False
        self.alarma_activada = False
        self.modo_luz_auto = True
        self.estado_actual_global = gl.ESTADO_NORMAL
        self.timer_puerta = None
        self.modo_ventilador_auto = True
        
        # ==========================================
        # CONFIGURACIÓN DEL BUZZER PASIVO
        # ==========================================
        self.buzzer_pwm = None
        self.buzzer_frecuencia = 1000
        self.buzzer_activo = False
        self.buzzer_silenciada = False  # <--- CORREGIDO: self en lugar de serf
        self.hilo_buzzer = None
        self.buzzer_ejecutando = False
        
        # Variables para botones (debounce)
        self.ultimo_boton = {'boton1': 0, 'boton2': 0, 'boton3': 0, 'boton4': 0}
        self.estado_boton = {'boton1': False, 'boton2': False, 'boton3': False, 'boton4': False}
        self.DEBOUNCE_MS = 150
        
        self._inicializar_gpio()
        self._inicializar_servo()
        self._inicializar_buzzer()
        
        self._actualizar_leds_estado(gl.ESTADO_NORMAL)
        self._set_buzzer(False)
        self._set_luces(False)

        self.estado_boton_anterior = {
            'boton1': False,
            'boton2': False,
            'boton3': False,
            'boton4': False
        }   

        self.servo_moviendo = False
        self.servo_tiempo_inicio = 0
        self.servo_duracion = 0.5            
        self.servo_estado_final = False
        
        if self.lcd_disponible:
            self.actualizar_lcd("Sistema Iniciado", "Esperando...")
        
        print("[ACTUADORES] Listo")
    
    def _inicializar_lcd(self):
        if not LCD_DISPONIBLE:
            return
        try:
            self.lcd = LCD(gl.LCD_I2C_ADDR, 1, gl.LCD_COLS, gl.LCD_ROWS, True)
            self.lcd.clear()
            self.lcd.text("Sistema Iniciado", 1)
            self.lcd.text("Esperando...", 2)
            self.lcd_disponible = True
            print(f"[LCD] Inicializado en 0x{gl.LCD_I2C_ADDR:02X}")
        except Exception as e:
            print(f"[LCD] No se pudo inicializar: {e}")
            self.lcd = None
            self.lcd_disponible = False
    
    def _inicializar_gpio(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        GPIO.setup(self.PIN_LED_PUERTA, GPIO.OUT)
        GPIO.setup(self.PIN_LED_VERDE, GPIO.OUT)
        GPIO.setup(self.PIN_LED_AMARILLO, GPIO.OUT)
        GPIO.setup(self.PIN_LED_ROJO, GPIO.OUT)
        GPIO.setup(self.PIN_LED_ZONA1, GPIO.OUT)
        GPIO.setup(self.PIN_LED_ZONA2, GPIO.OUT)
        GPIO.setup(self.PIN_LED_ZONA3, GPIO.OUT)
        GPIO.setup(self.PIN_LED_VENTILADOR, GPIO.OUT) 
        GPIO.setup(self.PIN_RELAY, GPIO.OUT)          
        GPIO.setup(self.PIN_BUZZER, GPIO.OUT)
        
        GPIO.setup(self.PIN_BOTON1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.PIN_BOTON2, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.PIN_BOTON3, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.PIN_BOTON4, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        GPIO.output(self.PIN_LED_PUERTA, False)
        GPIO.output(self.PIN_LED_VERDE, False)
        GPIO.output(self.PIN_LED_AMARILLO, False)
        GPIO.output(self.PIN_LED_ROJO, False)
        GPIO.output(self.PIN_LED_ZONA1, False)
        GPIO.output(self.PIN_LED_ZONA2, False)
        GPIO.output(self.PIN_LED_ZONA3, False)
        GPIO.output(self.PIN_LED_VENTILADOR, False)  
        GPIO.output(self.PIN_RELAY, False)         
        GPIO.output(self.PIN_BUZZER, False)
    
    def _inicializar_buzzer(self):
        try:
            self.buzzer_pwm = GPIO.PWM(self.PIN_BUZZER, self.buzzer_frecuencia)
            self.buzzer_pwm.start(0)
            print(f"[BUZZER] Inicializado con frecuencia {self.buzzer_frecuencia}Hz")
        except Exception as e:
            print(f"[BUZZER] Error inicializando PWM: {e}")
            self.buzzer_pwm = None
    
    def _inicializar_servo(self):
        GPIO.setup(self.PIN_SERVO, GPIO.OUT)
        self.servo_pwm = GPIO.PWM(self.PIN_SERVO, 50)
        self.servo_pwm.start(0)
        self.servo_pwm.ChangeDutyCycle(2.5)
        time.sleep(0.5)
        self.servo_pwm.ChangeDutyCycle(0)
    
    # ==========================================
    # CONTROL DEL BUZZER PASIVO
    # ==========================================
    
    def _set_buzzer(self, estado, frecuencia=None, duty_cycle=50):
        if not self.buzzer_pwm:
            return
        
        if estado:
            if frecuencia:
                self.buzzer_frecuencia = frecuencia
                self.buzzer_pwm.ChangeFrequency(frecuencia)
            self.buzzer_pwm.ChangeDutyCycle(duty_cycle)
            self.buzzer_activo = True
        else:
            self.buzzer_pwm.ChangeDutyCycle(0)
            self.buzzer_activo = False
    
    def activar_alarma(self, frecuencia=800):
        """
        Activa la alarma (SOLO para EMERGENCIA)
        Si está silenciada, NO suena
        """
        if self.buzzer_silenciada:
            print("[BUZZER] Silenciado - NO suena")
            return True
        
        self._set_buzzer(True, frecuencia, 50)
        self.alarma_activada = True
        return True
    
    def desactivar_alarma(self):
        """Desactiva la alarma (cuando la emergencia termina)"""
        self._set_buzzer(False)
        self.alarma_activada = False
        self.buzzer_silenciada = False  # Reiniciar silencio
        return True
    
    def silenciar_alarma(self):
        """
        Silencia el buzzer (mantiene la emergencia activa)
        Según el PDF: el usuario puede silenciar el buzzer
        pero la emergencia continúa (LED rojo sigue encendido)
        """
        self._set_buzzer(False)
        self.buzzer_silenciada = True
        self.alarma_activada = True  # Mantiene la emergencia activa
        print("[ALARMA] Silenciada (emergencia continúa)")
        return True
    
    def toggle_alarma(self):
        if self.alarma_activada:
            return self.desactivar_alarma()
        else:
            return self.activar_alarma()
    
    def alarma_emergencia(self):
        """Alarma de emergencia - sonido intermitente"""
        if self.buzzer_silenciada:
            print("[BUZZER] Silenciado - NO suena")
            return
        
        self.activar_alarma(800)
        secuencia = [
            (800, 0.5), (0, 0.2), (800, 0.5), (0, 0.2),
            (800, 0.3), (0, 0.1), (800, 0.3), (0, 0.1),
            (1200, 0.5)
        ]
        
        def _reproducir():
            self.buzzer_ejecutando = True
            for item in secuencia:
                if not self.alarma_activada or self.buzzer_silenciada:
                    break
                if isinstance(item, (list, tuple)):
                    freq, dur = item
                else:
                    freq = item
                    dur = 0.2
                if freq == 0:
                    self._set_buzzer(False)
                else:
                    self._set_buzzer(True, freq, 50)
                time.sleep(dur)
            self.buzzer_ejecutando = False
            if self.alarma_activada and not self.buzzer_silenciada:
                self._set_buzzer(True, 800, 50)
        
        if self.hilo_buzzer and self.hilo_buzzer.is_alive():
            return
        
        self.hilo_buzzer = threading.Thread(target=_reproducir)
        self.hilo_buzzer.daemon = True
        self.hilo_buzzer.start()
    
    # ==========================================
    # ACTUALIZAR ESTADO (MODIFICADO)
    # ==========================================
    
    def actualizar_estado(self, estado):
        """
        Actualiza LEDs de estado y alarma según el estado global.
        El buzzer SOLO suena en EMERGENCIA y si NO está silenciado.
        """
        self.estado_actual_global = estado
        self._actualizar_leds_estado(estado)
        
        if estado == gl.ESTADO_EMERGENCIA:
            self.alarma_activada = True
            if not self.buzzer_silenciada:
                self.activar_alarma(800)
            else:
                print("[BUZZER] Silenciado - manteniendo silencio")
        else:
            # Salir de emergencia: reiniciar todo
            self.desactivar_alarma()
    
    # ==========================================
    # RESTO DE MÉTODOS (SIN CAMBIOS)
    # ==========================================
    
    def actualizar_lcd(self, linea1, linea2):
        if not self.lcd_disponible or self.lcd is None:
            return
        try:
            linea1 = linea1[:16].ljust(16)
            linea2 = linea2[:16].ljust(16)
            self.lcd.clear()
            self.lcd.text(linea1, 1)
            self.lcd.text(linea2, 2)
        except Exception:
            self.lcd_disponible = False
            self.lcd = None
    
    def _set_luces(self, estado):
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
    
    def _actualizar_leds_estado(self, estado):
        GPIO.output(self.PIN_LED_VERDE, estado == gl.ESTADO_NORMAL)
        GPIO.output(self.PIN_LED_AMARILLO, estado == gl.ESTADO_ADVERTENCIA)
        GPIO.output(self.PIN_LED_ROJO, estado == gl.ESTADO_EMERGENCIA)
    
    def encender_ventilador(self):
        """Enciende el ventilador activando el relé"""
        GPIO.output(self.PIN_RELAY, True)           # Activa el relé
        self.ventilador_encendido = True
        GPIO.output(self.PIN_LED_VENTILADOR, True) 
        print("[VENTILADOR] Encendido (Relé activado)")
        return True

    def apagar_ventilador(self):
        """Apaga el ventilador desactivando el relé"""
        GPIO.output(self.PIN_RELAY, False)          # Desactiva el relé
        self.ventilador_encendido = False
        GPIO.output(self.PIN_LED_VENTILADOR, False)
        print("[VENTILADOR] Apagado (Relé desactivado)")
        return True
    
    def toggle_ventilador(self):
        if self.ventilador_encendido:
            return self.apagar_ventilador()
        else:
            return self.encender_ventilador()

    def set_modo_ventilador(self, auto=True):
        self.modo_ventilador_auto = auto
        return True

    def toggle_modo_ventilador(self):
        self.modo_ventilador_auto = not self.modo_ventilador_auto
        return self.modo_ventilador_auto

    def abrir_puerta(self):
        self.servo_pwm.ChangeDutyCycle(9.72)  # 130°
        time.sleep(0.5)
        self.servo_pwm.ChangeDutyCycle(0)
        GPIO.output(self.PIN_LED_PUERTA, True)
        self.puerta_abierta = True
        self._cancelar_timer_puerta()
        print("[PUERTA] Abierta")
        return True

    def actualizar_servo(self):
        """Actualiza el estado del servo (llamar en cada ciclo del loop)"""
        if self.servo_moviendo:
            if time.time() - self.servo_tiempo_inicio >= self.servo_duracion:
                self.servo_pwm.ChangeDutyCycle(0)
                GPIO.output(self.PIN_LED_PUERTA, self.servo_estado_final)
                self.servo_moviendo = False
                if self.servo_estado_final:
                    print("[PUERTA] Abierta")
                else:
                    print("[PUERTA] Cerrada")
    
    def cerrar_puerta(self):
        self.servo_pwm.ChangeDutyCycle(2.5)   # 0°
        time.sleep(0.5)
        self.servo_pwm.ChangeDutyCycle(0)
        GPIO.output(self.PIN_LED_PUERTA, False)
        self.puerta_abierta = False
        self._cancelar_timer_puerta()
        print("[PUERTA] Cerrada")
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
    
    def leer_botones(self):
        """Lee los botones con deteccion de flanco de bajada + debounce por tiempo"""
        t_actual = time.time() * 1000
        resultado = {}
        DEBOUNCE_MS = 150  # ajustá según tus pruebas (50-300ms típico)

        botones = {
            'boton1': self.PIN_BOTON1,
            'boton2': self.PIN_BOTON2,
            'boton3': self.PIN_BOTON3,
            'boton4': self.PIN_BOTON4,
        }

        for nombre, pin in botones.items():
            estado_actual = GPIO.input(pin) == 0
            fue_presionado = estado_actual and not self.estado_boton_anterior[nombre]

            if fue_presionado:
                tiempo_desde_ultimo = t_actual - self.ultimo_boton.get(nombre, 0)
                if tiempo_desde_ultimo > DEBOUNCE_MS:
                    self.ultimo_boton[nombre] = t_actual
                    resultado[nombre] = True
                    print(f"[{nombre.upper()}] Presionado")

            self.estado_boton_anterior[nombre] = estado_actual

        return resultado
        
    def obtener_estados(self):
        return {
            'puerta': 'ABIERTA' if self.puerta_abierta else 'CERRADA',
            'luces': 'ENCENDIDAS' if self.luces_encendidas else 'APAGADAS',
            'modo_luz': 'AUTOMATICO' if self.modo_luz_auto else 'MANUAL',
            'ventilador': 'ENCENDIDO' if self.ventilador_encendido else 'APAGADO',
            'alarma': 'ACTIVADA' if self.alarma_activada else 'DESACTIVADA'
        }
    
    def __del__(self):
        try:
            if hasattr(self, 'servo_pwm'):
                self.servo_pwm.stop()
            if self.buzzer_pwm:
                self.buzzer_pwm.stop()
            if self.lcd_disponible and self.lcd:
                self.lcd.clear()
                self.lcd.backlight(False)
        except:
            pass
        GPIO.cleanup()