# ==========================================
# ESTADOS DEL SISTEMA
# ==========================================
ESTADO_NORMAL = "NORMAL"
ESTADO_ADVERTENCIA = "ADVERTENCIA"
ESTADO_EMERGENCIA = "EMERGENCIA"

# ==========================================
# UMBRALES DE SENSORES
# ==========================================
UMBRAL_TEMP_ALTA = 28.0
UMBRAL_HUMEDAD_MIN = 30.0
UMBRAL_HUMEDAD_MAX = 70.0
UMBRAL_GAS_PELIGRO = 300
UMBRAL_LUZ_BAJA = 300
UMBRAL_DISTANCIA_APERTURA = 15.0

# ==========================================
# CONFIGURACIÓN MQTT
# ==========================================
CARNE = "202500177"
BROKER = "broker.emqx.io"
PORT = 1883
TOPIC_BASE = f"{CARNE}/edificio"

# ==========================================
# TIEMPOS (segundos)
# ==========================================
CICLO_PRINCIPAL = 0.5
TIEMPO_PUERTA_ABIERTA = 5
TIEMPO_ROTACION_LCD = 4

# Para el ciclo no bloqueante
INTERVALO_LECTURA = 0.5   # 500ms entre lecturas

# ==========================================
# PUERTO SERIAL PARA ARDUINO (solo sensores)
# ==========================================
PUERTO_SERIAL = "/dev/ttyUSB0"

# ==========================================
# RUTA DEL BINARIO ARM64
# ==========================================
ARM64_BIN_PATH = "./arm64_stats"

# ==========================================
# PINES GPIO (Raspberry Pi)
# ==========================================

# ---- SENSORES ----
PIN_DHT = 5           # GPIO5  - Pin 29 (DHT11)
PIN_TRIG = 17         # GPIO17 - Pin 11 (HC-SR04 TRIG)
PIN_ECHO = 27         # GPIO27 - Pin 13 (HC-SR04 ECHO)

# ---- ACTUADORES ----
PIN_SERVO = 18        # GPIO18 - Pin 12 (Servomotor)
PIN_RELAY = 11        # GPIO11 - Pin 23 (VENTILADOR)

# ---- LEDs DE ILUMINACIÓN (3 ZONAS) ----
PIN_LED_ZONA1 = 6     # GPIO6  - Pin 31
PIN_LED_ZONA2 = 12    # GPIO12 - Pin 32
PIN_LED_ZONA3 = 13    # GPIO13 - Pin 33

# ---- LEDs DE ESTADO ----
PIN_LED_VERDE = 16    # GPIO16 - Pin 36 (NORMAL)
PIN_LED_AMARILLO = 20 # GPIO20 - Pin 38 (ADVERTENCIA)
PIN_LED_ROJO = 21     # GPIO21 - Pin 40 (EMERGENCIA)

# ---- LEDs INDICADORES ----
PIN_LED_PUERTA = 10   # GPIO19 - Pin 35 (LED indicador de puerta)
PIN_LED_VENTILADOR = 9 # GPIO9  - Pin 21 (LED indicador de ventilación)

# ---- BUZZER ----
PIN_BUZZER = 26       # GPIO26 - Pin 37

# ---- BOTONES ----
PIN_BOTON1 = 22       # GPIO22 - Pin 15
PIN_BOTON2 = 23       # GPIO23 - Pin 16
PIN_BOTON3 = 24       # GPIO24 - Pin 18
PIN_BOTON4 = 25       # GPIO25 - Pin 22

# ==========================================
# LCD I2C (Raspberry Pi)
# ==========================================
LCD_I2C_ADDR = 0x27
LCD_COLS = 16
LCD_ROWS = 2