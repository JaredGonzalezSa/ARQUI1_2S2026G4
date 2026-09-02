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