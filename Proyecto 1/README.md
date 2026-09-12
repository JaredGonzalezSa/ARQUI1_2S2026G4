# Edificio Inteligente IoT con Raspberry Pi ARM64

<div align="center">

![Python](https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white)
![ARM64](https://img.shields.io/badge/Ensamblador-AArch64-8A2BE2)
![MQTT](https://img.shields.io/badge/MQTT-EMQX-660066?logo=mqtt&logoColor=white)
![MongoDB](https://img.shields.io/badge/Base%20de%20datos-MongoDB%20Atlas-47A248?logo=mongodb&logoColor=white)
![Estado](https://img.shields.io/badge/Estado-En%20desarrollo-yellow)

</div>

## Acerca del proyecto

Esta carpeta contiene la implementación del Proyecto 1: Edificio Inteligente IoT con Raspberry Pi ARM64. El sistema integra hardware, software y procesamiento de bajo nivel para controlar y monitorear una maqueta de un edificio inteligente.

La solución utiliza una Raspberry Pi con Linux de 64 bits como plataforma principal, Python para la lógica del sistema, MQTT con EMQX para la comunicación entre módulos, MongoDB Atlas para la persistencia de información, un dashboard web con Flask para supervisión y control remoto, y un módulo desarrollado en ensamblador AArch64 para procesar lecturas reales de temperatura.

---

## Objetivos

- Monitorear en tiempo real temperatura, humedad, gas o humo, distancia y nivel de luz.
- Automatizar la respuesta de ventilación, iluminación, acceso y alarma según las condiciones detectadas.
- Mantener un estado global del edificio: NORMAL, ADVERTENCIA o EMERGENCIA.
- Comunicar lecturas, estados y comandos mediante MQTT.
- Almacenar lecturas, eventos, comandos, estados y resultados en MongoDB Atlas.
- Permitir supervisión y control remoto desde un dashboard web.
- Procesar lecturas reales con un módulo en ensamblador ARM64, calculando máximo, mínimo, promedio entero y cantidad de datos.

---

## Funcionalidades principales

| Subsistema                    | Funcionalidad                                                                                                                          |
| ----------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| 🌡️ **Monitoreo ambiental**     | Lectura de temperatura y humedad mediante DHT11, control automático del ventilador y generación de advertencias.                       |
| 🚨 **Detección de gas/humo**   | Monitoreo del nivel de gas, activación de buzzer y LED de emergencia, apertura automática de la puerta y cambio a estado `EMERGENCIA`. |
| 🚪 **Acceso automatizado**     | Medición de distancia con HC-SR04 y control de puerta mediante servomotor, botón físico o dashboard.                                   |
| 💡 **Iluminación inteligente** | Control de tres zonas de iluminación con modos `AUTOMÁTICO` y `MANUAL`.                                                                |
| 🚦 **Estado global**           | Estados `NORMAL`, `ADVERTENCIA` y `EMERGENCIA`, representados mediante LEDs y publicados por MQTT.                                     |
| 🎛️ **Panel físico**            | LCD y cuatro botones para puerta, modo de iluminación, silenciar alarma y restablecer alerta.                                          |
| 🌐 **Dashboard web**           | Visualización en tiempo real, gráficas históricas, estado de actuadores, controles remotos, eventos y resultados ARM64.                |
| 🧠 **Procesamiento ARM64**     | Generación de `datos.txt`, ejecución del programa AArch64 y lectura de `resultado.txt` con estadísticas.                               |

---

## Estructura del proyecto

```text
/
├── 📁 backend/                         # Backend web y comunicación con el dashboard
│   ├── app.py                         # Servidor Flask, API HTTP y cliente MQTT
│   ├── mongo.py                       # Acceso y operaciones sobre MongoDB Atlas
│   ├── requirements.txt               # Dependencias del backend
│   ├── 📁 static/
│   │   └── 📁 img/                    # Recursos gráficos del dashboard
│   │       ├── 📁 control/            # Iconos de controles y actuadores
│   │       └── 📁 sensores/           # Iconos de sensores
│   └── 📁 templates/
│       └── index.html                 # Interfaz web, estilos y lógica del dashboard
│
├── 📁 iot/                             # Software ejecutado en la Raspberry Pi
│   ├── main.py                        # Punto de entrada y ciclo principal del sistema IoT
│   ├── globals.py                     # Pines GPIO, MQTT, umbrales, tiempos y configuración
│   ├── arm64_integracion.py           # Integración entre Python y el módulo ARM64
│   ├── arm64_stats.s                  # Código fuente del módulo en AArch64
│   ├── arm64_stats                    # Binario ejecutable del módulo ARM64
│   ├── limpiar_retain.py              # Limpieza de mensajes retenidos en MQTT
│   ├── test.py                        # Prueba rápida de los botones físicos
│   ├── requirements.txt               # Dependencias del núcleo IoT
│   └── 📁 core/
│       ├── __init__.py
│       ├── sensores.py                # Lectura y administración de sensores
│       └── actuadores.py              # Control de actuadores, LCD y botones
│
├── 📁 scripts/                         # Pruebas aisladas de hardware y servicios
│   ├── lcd_test.py                    # Prueba de comunicación con la pantalla LCD
│   ├── leds_test.py                   # Prueba secuencial de LEDs de iluminación
│   ├── test_buzzer.py                 # Prueba del buzzer
│   ├── test_dht11.py                  # Prueba del sensor DHT11
│   ├── test_leds.py                   # Prueba interactiva de LEDs de estado e iluminación
│   ├── test_mongo.py                  # Prueba de conexión y escritura en MongoDB Atlas
│   ├── test_mqtt_pub.py               # Prueba de publicación MQTT
│   └── test_mqtt_sub.py               # Prueba de suscripción MQTT
│
├── 📁 docs/
│   └── manual-tecnico.md              # Documentación técnica completa del sistema
│
├── .gitignore                         # Archivos y directorios excluidos del repositorio
└── README.md                          # Descripción general, configuración y acceso a la documentación
```

---

## Tecnologías y herramientas

| Categoría           | Tecnologías                                                                                           |
| ------------------- | ----------------------------------------------------------------------------------------------------- |
| 💻 **Lenguajes**     | Python 3, Ensamblador AArch64                                                                         |
| ⚙️ **Backend web**   | Flask                                                                                                 |
| 🎨 **Frontend web**  | HTML, CSS, JavaScript                                                                                 |
| 📡 **Comunicación**  | MQTT, EMQX                                                                                            |
| 🗄️ **Base de datos** | MongoDB Atlas                                                                                         |
| 🔧 **Hardware**      | Raspberry Pi, DHT11, HC-SR04, sensor de gas, LDR, servomotor, buzzer, ventilador, LCD, LEDs y botones |


---

## Configuración básica

### 1. Clonar el repositorio

```bash
git clone https://github.com/JaredGonzalezSa/ARQUI1_2S2026G4
cd ARQUI1_2S2026G4
```

### 2. Crear la variable de entorno de MongoDB

Crear un archivo `.env` con:

```env
MONGO_URI=<CADENA_DE_CONEXION_MONGODB_ATLAS>
```

### 3. Ejecutar el dashboard

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

El servidor Flask se inicia en:

```text
http://localhost:5000
```

### 4. Preparar el entorno IoT en Raspberry Pi

```bash
cd iot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

El núcleo IoT se ejecuta sobre la Raspberry Pi con acceso a los sensores, actuadores, GPIO y puerto serial configurados para la maqueta.

## Documentación

La documentación técnica completa del sistema se encuentra en:

- [Manual técnico](docs/manual-tecnico.md)

El manual explica la arquitectura implementada, los subsistemas, el flujo MQTT, el modelo de datos en MongoDB Atlas, el backend/dashboard, la puesta en marcha y el funcionamiento del módulo ARM64. Los diagramas se manejan como entregables separados.

- [Diagrama de arquitectura](docs/diagrama-arquitectura.svg)

El diagrama de arquitectura muestra la organización general del sistema y la interacción entre la Raspberry Pi, los sensores y actuadores, el broker MQTT, MongoDB Atlas, el dashboard web y el módulo de procesamiento ARM64.

- [Diagrama de conexiones y flujo](docs/diagrama-conexiones-flujo.png)

El diagrama de conexiones y flujo representa las conexiones entre los componentes físicos del edificio inteligente y el recorrido de la información dentro del sistema, incluyendo la adquisición de datos, comunicación mediante MQTT, almacenamiento en MongoDB, control desde el dashboard y el flujo de procesamiento Python -> datos.txt -> ARM64 -> resultado.txt -> Python -> MongoDB Atlas -> Dashboard.