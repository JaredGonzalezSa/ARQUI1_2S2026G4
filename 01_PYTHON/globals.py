# ==========================================
# ESTADOS DEL SISTEMA
# ==========================================
ESTADO_NORMAL = "NORMAL"
ESTADO_ADVERTENCIA = "ADVERTENCIA"
ESTADO_EMERGENCIA = "EMERGENCIA"

# ==========================================
# UMBRALES DE SENSORES
# ==========================================
# Estos valores dictarán cuándo el sistema cambia de estado y activa actuadores
UMBRAL_TEMP_ALTA = 28.0       # Temperatura en °C para activar ventilador (ADVERTENCIA)
UMBRAL_HUMEDAD_MIN = 30.0     # Límite inferior de humedad aceptable
UMBRAL_HUMEDAD_MAX = 70.0     # Límite superior de humedad aceptable
UMBRAL_GAS_PELIGRO = 400.0    # Valor del MQ-2 para activar alarma (EMERGENCIA)
UMBRAL_LUZ_OSCURO = 300.0     # Valor del LDR para encender luces automáticamente
DISTANCIA_PUERTA_CM = 15.0    # Distancia en cm para que el HC-SR04 abra la puerta

# ==========================================
# CONFIGURACIÓN MQTT
# ==========================================
CARNE = "202500177"
BROKER = "broker.emqx.io"
PORT = 1883
TOPIC_BASE = f"{CARNE}/edificio"

# ==========================================
# Tiempos (segundos)
# ==========================================
CICLO_PRINCIPAL = 5
TIEMPO_PUERTA_ABIERTA = 5

# ==========================================
# PUERTO SERIAL PARA ARDUINO
# ==========================================
PUERTO_SERIAL = "/dev/ttyUSB0"

# ==========================================
# PINES GPIO (Raspberry Pi)
# ==========================================
PIN_DHT = 5         # GPIO22 para LED de puerta
PIN_TRIG = 17       # GPIO22 para LED de puerta
PIN_ECHO = 27       # GPIO22 para LED de puerta
PIN_SERVO = 18      # GPIO22 para LED de puerta
PIN_VENTILADOR = 4  # para Ventilador
PIN_LED_PUERTA = 1 # GPIO22 para LED de puerta

# LEDs de estado del sistema
PIN_LED_VERDE = 16
PIN_LED_AMARILLO = 20
PIN_LED_ROJO = 21

# LEDs de iluminacion (3 zonas)
PIN_LED_ZONA1 = 6   # Zona 1
PIN_LED_ZONA2 = 12   # Zona 2
PIN_LED_ZONA3 = 13   # Zona 3

# Buzzer
PIN_BUZZER = 26

# Botones
PIN_BOTON1 = 22     # Abrir/cerrar puerta
PIN_BOTON2 = 23     # Cambiar modo iluminación
PIN_BOTON3 = 24     # Silenciar alarma
PIN_BOTON4 = 25     # Restablecer alerta

