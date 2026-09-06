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
UMBRAL_GAS_PELIGRO = 400
UMBRAL_LUZ_BAJA = 500
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
TIEMPO_ROTACION_LCD = 4          # Cada 4 segundos cambia de pantalla

# ==========================================
# PUERTO SERIAL PARA ARDUINO (solo sensores)
# ==========================================
PUERTO_SERIAL = "/dev/ttyUSB0"

# ==========================================
# RUTA DEL BINARIO ARM64
# ==========================================


# ==========================================
# PINES GPIO (Raspberry Pi)
# ==========================================
PIN_DHT = 5
PIN_TRIG = 17
PIN_ECHO = 27
PIN_SERVO = 18
PIN_VENTILADOR = 4
PIN_LED_PUERTA = 19
PIN_LED_VERDE = 16
PIN_LED_AMARILLO = 20
PIN_LED_ROJO = 21
PIN_LED_ZONA1 = 6
PIN_LED_ZONA2 = 12
PIN_LED_ZONA3 = 13
PIN_BUZZER = 26
PIN_BOTON1 = 22
PIN_BOTON2 = 23
PIN_BOTON3 = 24
PIN_BOTON4 = 25

# ==========================================
# LCD I2C (Raspberry Pi)
# ==========================================
LCD_I2C_ADDR = 0x27  
LCD_COLS = 16
LCD_ROWS = 2