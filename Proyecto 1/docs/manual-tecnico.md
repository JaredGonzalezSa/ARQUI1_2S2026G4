# Manual técnico

## Índice

1. [Visión general](#1-visión-general)
2. [Conceptos mínimos para comprender el proyecto](#2-conceptos-mínimos-para-comprender-el-proyecto)
3. [Arquitectura del sistema](#3-arquitectura-del-sistema)
4. [Estructura del repositorio](#4-estructura-del-repositorio)
5. [Configuración central del sistema](#5-configuración-central-del-sistema)
6. [Adquisición de sensores](#6-adquisición-de-sensores)
7. [Control de actuadores y panel físico](#7-control-de-actuadores-y-panel-físico)
8. [Subsistemas de automatización](#8-subsistemas-de-automatización)
9. [Estado global del edificio](#9-estado-global-del-edificio)
10. [Flujo MQTT](#10-flujo-mqtt)
11. [Modelo de datos en MongoDB Atlas](#11-modelo-de-datos-en-mongodb-atlas)
12. [Backend Flask y dashboard web](#12-backend-flask-y-dashboard-web)
13. [Módulo de procesamiento ARM64](#13-módulo-de-procesamiento-arm64)
14. [Puesta en marcha](#14-puesta-en-marcha)
15. [Pruebas y diagnóstico](#15-pruebas-y-diagnóstico)
16. [Decisiones de diseño](#16-decisiones-de-diseño)
17. [Consideraciones de la implementación actual](#17-consideraciones-de-la-implementación-actual)
18. [Glosario](#18-glosario)

---

# 1. Visión general

## 1.1 ¿Qué construye este proyecto?

El proyecto implementa el sistema de control y monitoreo de una maqueta de edificio inteligente. La solución combina hardware físico, software de alto nivel, comunicación por mensajería, persistencia de datos y procesamiento de bajo nivel en ensamblador AArch64.

La **Raspberry Pi** es el controlador principal. Sobre ella se ejecuta la lógica IoT escrita en Python, se leen sensores, se controlan actuadores, se evalúan condiciones de seguridad y se ejecuta el programa ARM64. Además, un **Arduino** funciona como controlador auxiliar de adquisición para los sensores de gas y luz. El Arduino se comunica con la Raspberry Pi mediante una conexión serial sobre USB; no se emplean directamente los pines TX y RX de la Raspberry Pi para esa comunicación.

El sistema también incorpora un **backend web desarrollado con Flask**. Este backend se conecta al mismo broker MQTT utilizado por la Raspberry Pi, mantiene en memoria el estado más reciente recibido, consulta el historial almacenado en MongoDB Atlas y expone una API HTTP que utiliza el navegador.

El **dashboard web** permite observar lecturas y estados, revisar gráficas e historial y enviar órdenes de control remoto. El navegador no controla directamente los GPIO ni se comunica directamente con la Raspberry Pi: envía una petición HTTP al backend Flask y este transforma la solicitud en un mensaje MQTT.

Finalmente, el proyecto contiene un programa escrito en **ensamblador AArch64**. Python genera un archivo de temperaturas enteras, ejecuta el binario ARM64 y recupera las estadísticas calculadas por el ensamblador: máximo, mínimo, promedio entero y cantidad de valores procesados.

## 1.2 Responsabilidad de cada componente

| Componente        | Responsabilidad dentro del proyecto                                                                                                             |
| ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| Raspberry Pi      | Ejecuta la lógica principal de automatización, accede a GPIO, se comunica con Arduino, publica/recibe MQTT, escribe en MongoDB y ejecuta ARM64. |
| Arduino           | Adquiere los valores de gas y luz y los transmite a la Raspberry Pi mediante serial por USB.                                                    |
| `iot/main.py`     | Coordina el sistema IoT: sensores, actuadores, estados, MQTT, persistencia y procesamiento ARM64.                                               |
| `SensorManager`   | Centraliza la adquisición de temperatura, humedad, distancia, gas y luz.                                                                        |
| `ActuadorManager` | Centraliza servo, LEDs, ventilador, buzzer, botones y LCD.                                                                                      |
| EMQX              | Broker MQTT que intermedia los mensajes publicados entre Raspberry Pi y backend.                                                                |
| MongoDB Atlas     | Conserva lecturas, eventos, comandos, estados globales y resultados ARM64.                                                                      |
| Flask             | Sirve el dashboard, recibe MQTT, consulta MongoDB y expone las rutas HTTP utilizadas por el frontend.                                           |
| Dashboard         | Presenta datos al usuario y permite enviar acciones de control remoto.                                                                          |
| `arm64_stats`     | Procesa `datos.txt` en AArch64 y produce `resultado.txt`.                                                                                       |

## 1.3 Recorrido general de la información

Una lectura normal del sistema sigue esta lógica:

1. El sensor produce una medición.
2. `SensorManager` obtiene el valor, ya sea directamente desde la Raspberry Pi o desde el Arduino por serial.
3. `iot/main.py` publica la lectura en MQTT.
4. El backend Flask, suscrito al namespace MQTT del edificio, recibe el mensaje y actualiza el valor más reciente en memoria.
5. El navegador consulta periódicamente `/api/datos` y representa ese estado en el dashboard.
6. De forma independiente, `iot/main.py` guarda lecturas en MongoDB Atlas para disponer de historial.
7. El dashboard consulta `/api/historial` para obtener datos históricos desde MongoDB.

Un comando remoto recorre el camino inverso a nivel funcional:

1. El usuario presiona un control del dashboard.
2. JavaScript envía una solicitud `POST` a `/api/control`.
3. Flask traduce la acción a uno de los comandos definidos por el sistema.
4. Flask publica ese comando en el topic MQTT de control remoto.
5. `iot/main.py` recibe el mensaje.
6. `ActuadorManager` ejecuta la acción física correspondiente.
7. La acción se registra en MongoDB y el nuevo estado se publica de nuevo por MQTT.
8. Flask recibe el estado publicado y el dashboard termina reflejando el cambio.

---

# 2. Conceptos mínimos para comprender el proyecto

Esta sección no pretende enseñar cada tecnología de forma completa. Solo introduce los conceptos que aparecen directamente en la implementación.

## 2.1 Raspberry Pi y GPIO

Una Raspberry Pi es una computadora de propósito general que, además de ejecutar Linux, expone pines físicos de entrada y salida. Estos pines se conocen como **GPIO** (*General Purpose Input/Output*).

El proyecto utiliza la numeración **BCM**, configurada mediante:

```python
GPIO.setmode(GPIO.BCM)
```

Por esta razón, cuando el código habla de `GPIO17`, `GPIO18`, etc., se refiere al número BCM y no necesariamente al número físico impreso en el conector de 40 pines.

Los GPIO del proyecto se utilizan para funciones como:

- generar el pulso del sensor ultrasónico;
- recibir el eco del HC-SR04;
- controlar el servomotor mediante PWM;
- activar el relé del ventilador;
- encender LEDs;
- producir sonido con el buzzer;
- leer los cuatro botones físicos.

## 2.2 Arduino y lectura analógica

Algunos sensores entregan una señal analógica. La Raspberry Pi no dispone de entradas analógicas de propósito general integradas, por lo que el proyecto delega las lecturas de **gas** y **luz** a un Arduino.

El Arduino funciona como controlador auxiliar: adquiere esas señales y envía a la Raspberry Pi una línea de texto por serial. El formato que espera el software de la Raspberry es:

```text
GAS:250,LUZ:480
```

En esta versión del repositorio no se incluye el firmware del Arduino. Por ello, este manual puede documentar con precisión el protocolo que recibe Python, pero no la implementación interna con la que el Arduino obtiene o transforma las lecturas.

## 2.3 Comunicación serial sobre USB

Aunque el Arduino se conecta físicamente mediante USB, Linux expone la conexión como un **puerto serial**. La ruta configurada en el proyecto es:

```text
/dev/ttyUSB0
```

Python abre ese dispositivo a `9600` baudios mediante `pyserial`. Para el software, la comunicación se comporta como un flujo de texto serial aunque el cable utilizado sea USB.

## 2.4 MQTT

MQTT es un protocolo de mensajería basado en **publicación/suscripción**.

Los componentes no necesitan enviarse datos directamente entre sí. En su lugar:

- un componente **publica** un mensaje en un *topic*;
- otro componente se **suscribe** al topic;
- un **broker** recibe el mensaje y lo distribuye a los suscriptores.

En este proyecto el broker es `broker.emqx.io`. La Raspberry Pi y el backend Flask son clientes MQTT diferentes conectados al mismo broker.

## 2.5 MongoDB

MongoDB es una base de datos orientada a documentos. En lugar de organizar toda la información como filas de tablas relacionales, almacena documentos similares a objetos JSON/BSON dentro de **colecciones**.

El proyecto utiliza la base:

```text
edificio_iot
```

Cada tipo de información se conserva en una colección diferente: lecturas, eventos, comandos, resultados ARM64 y estados globales.

## 2.6 Flask, HTTP y API

Flask es el framework web utilizado por el backend. Tiene dos responsabilidades principales:

1. servir la interfaz HTML del dashboard;
2. exponer rutas HTTP que JavaScript puede consultar.

Las rutas principales son:

- `GET /api/datos` para el estado actual;
- `GET /api/historial` para información histórica;
- `POST /api/control` para enviar órdenes remotas.

## 2.7 ARM64 y AArch64

**ARM64** describe la arquitectura ARM de 64 bits. **AArch64** es el estado de ejecución y el conjunto de instrucciones de 64 bits utilizado para programar esta arquitectura.

El módulo `arm64_stats.s` trabaja mucho más cerca del procesador que Python: utiliza registros, instrucciones aritméticas, saltos y llamadas al sistema de Linux para abrir, leer, crear y escribir archivos.

---

# 3. Arquitectura del sistema

## 3.1 Controlador principal: Raspberry Pi

La Raspberry Pi concentra la lógica central del edificio. El archivo [`iot/main.py`](../iot/main.py) instancia tres objetos fundamentales:

- `MongoDBManager`, encargado de las escrituras a MongoDB;
- `SensorManager`, encargado de obtener mediciones;
- `ActuadorManager`, encargado del hardware de salida y del panel físico.

También crea un cliente MQTT propio. Ese cliente publica datos y se suscribe al canal de control remoto.

La Raspberry Pi no se limita a reenviar lecturas: mantiene reglas de automatización. A partir de temperatura, humedad, gas, distancia y luz decide el estado global y controla ventilación, iluminación, alarma y puerta.

## 3.2 Controlador auxiliar: Arduino

El código de [`iot/core/sensores.py`](../iot/core/sensores.py) muestra que los valores de `gas` y `luz` no se obtienen desde GPIO de la Raspberry. Se reciben desde el puerto serial configurado en `/dev/ttyUSB0`.

Al inicializar `SensorManager`, Python:

1. intenta abrir el puerto a `9600` baudios;
2. crea un hilo en segundo plano;
3. el hilo permanece leyendo líneas seriales;
4. cada línea se divide por comas;
5. los pares `GAS:<valor>` y `LUZ:<valor>` actualizan las últimas mediciones disponibles.

Esta separación permite que la Raspberry Pi utilice valores de sensores analógicos sin incorporar un ADC externo directamente en su lógica Python.

## 3.3 Capa de mensajería: EMQX

El sistema usa el broker público:

```text
broker.emqx.io:1883
```

El namespace base configurado es:

```text
202500177/edificio
```

`iot/main.py` publica las lecturas y estados. Por otra parte, [`backend/app.py`](../backend/app.py) se suscribe a:

```text
202500177/edificio/#
```

El comodín `#` indica que Flask desea recibir todos los topics que comiencen con el prefijo del edificio.

## 3.4 Persistencia: MongoDB Atlas

La escritura a base de datos está encapsulada principalmente en [`backend/mongo.py`](../backend/mongo.py). Aunque el archivo se encuentra en `backend/`, `iot/main.py` agrega esa carpeta a `sys.path` e importa `MongoDBManager` para utilizar el mismo componente desde el núcleo IoT.

El dashboard, en cambio, utiliza una conexión `MongoClient` en `backend/app.py` para realizar consultas de historial.

Por tanto, en la implementación existen dos formas de acceso con responsabilidades distintas:

- `MongoDBManager`: operaciones de escritura efectuadas por el núcleo IoT;
- `MongoClient` dentro de Flask: consultas históricas para el dashboard.

## 3.5 Capa web: Flask y navegador

El navegador no se suscribe directamente a MQTT. El backend Flask actúa como intermediario.

Flask mantiene un diccionario `datos` en memoria con los valores actuales. Cuando recibe mensajes MQTT, actualiza ese diccionario. El navegador consulta `/api/datos` cada `500 ms` y actualiza los elementos visibles.

Para datos históricos, el navegador consulta `/api/historial` cada `5 s`. Esa ruta recupera documentos de MongoDB Atlas.

## 3.6 Procesamiento de bajo nivel

El procesamiento ARM64 se encuentra en tres piezas:

- [`iot/core/sensores.py`](../iot/core/sensores.py): genera `datos.txt`;
- [`iot/arm64_integracion.py`](../iot/arm64_integracion.py): ejecuta el binario y lee `resultado.txt`;
- [`iot/arm64_stats.s`](../iot/arm64_stats.s): realiza los cálculos en AArch64.

`iot/main.py` coordina todo el ciclo y publica el resultado final mediante MQTT, además de persistirlo en MongoDB.

---

# 4. Estructura del repositorio

La organización relevante de esta versión del proyecto es:

```text
Proyecto 1/
├── backend/
│   ├── app.py
│   ├── mongo.py
│   ├── requirements.txt
│   ├── static/
│   │   └── img/
│   └── templates/
│       └── index.html
├── iot/
│   ├── main.py
│   ├── globals.py
│   ├── arm64_integracion.py
│   ├── arm64_stats.s
│   ├── arm64_stats
│   ├── limpiar_retain.py
│   ├── requirements.txt
│   └── core/
│       ├── __init__.py
│       ├── sensores.py
│       └── actuadores.py
├── scripts/
│   ├── lcd_test.py
│   ├── leds_test.py
│   ├── test_buzzer.py
│   ├── test_dht11.py
│   ├── test_leds.py
│   ├── test_mongo.py
│   ├── test_mqtt_pub.py
│   └── test_mqtt_sub.py
├── docs/
│   └── manual-tecnico.md
├── .gitignore
└── README.md
```

## 4.1 `iot/`

Contiene el software que se ejecuta junto al hardware del edificio.

### `main.py`

Es el punto central de integración. Se encarga de:

- inicializar sensores y actuadores;
- conectarse a MQTT;
- escuchar comandos remotos;
- leer sensores en diferentes intervalos;
- leer botones físicos;
- persistir lecturas;
- actualizar el LCD;
- evaluar NORMAL, ADVERTENCIA y EMERGENCIA;
- aplicar automatización de iluminación, ventilación y acceso;
- ejecutar periódicamente ARM64;
- publicar los estados resultantes.

### `globals.py`

Centraliza las constantes de hardware y comportamiento: GPIO, umbrales, broker, topic base, puerto serial y tiempos generales.

### `core/sensores.py`

Implementa `SensorManager`. Contiene la adquisición del DHT11, HC-SR04 y recepción serial de gas y luz.

### `core/actuadores.py`

Implementa `ActuadorManager`. Contiene servo, iluminación, relé del ventilador, buzzer, LEDs de estado, LCD y botones.

### `arm64_stats.s`

Programa AArch64 que lee `datos.txt`, obtiene estadísticas y crea `resultado.txt`.

### `arm64_integracion.py`

Es la capa de integración entre Python y el binario ARM64. Selecciona ejecución nativa o mediante QEMU dependiendo de la arquitectura del equipo.

## 4.2 `backend/`

Contiene el servidor web y la capa de persistencia reutilizada por el núcleo IoT.

### `app.py`

Implementa:

- servidor Flask;
- cliente MQTT del dashboard;
- estado actual en memoria;
- consulta de historial;
- API de control remoto.

### `mongo.py`

Implementa `MongoDBManager` y define las colecciones utilizadas por el sistema.

### `templates/index.html`

Contiene la interfaz del dashboard, sus estilos y JavaScript. Utiliza Chart.js desde CDN para las gráficas.

## 4.3 `scripts/`

Contiene utilidades de prueba aislada para hardware, MQTT y MongoDB. Estas herramientas son especialmente útiles antes de ejecutar la integración completa.

---

# 5. Configuración central del sistema

La configuración principal se encuentra en [`iot/globals.py`](../iot/globals.py).

## 5.1 Estados

```text
NORMAL
ADVERTENCIA
EMERGENCIA
```

## 5.2 Umbrales implementados

| Variable         | Valor configurado | Uso actual                                                                          |
| ---------------- | ----------------: | ----------------------------------------------------------------------------------- |
| Temperatura alta |           `28 °C` | Si `temperatura > 28`, el sistema entra en ADVERTENCIA.                             |
| Humedad mínima   |            `30 %` | Valores menores contribuyen a ADVERTENCIA.                                          |
| Humedad máxima   |            `70 %` | Valores mayores contribuyen a ADVERTENCIA.                                          |
| Gas peligroso    |             `300` | Si `gas > 300`, el sistema entra en EMERGENCIA.                                     |
| Luz              |             `300` | En modo automático, la implementación actual enciende las luces cuando `luz > 300`. |
| Distancia        |           `15 cm` | Si `distancia < 15`, la puerta se abre temporalmente.                               |

> **Nota sobre la luz:** el código de Raspberry Pi compara el valor recibido con `300`, pero el firmware del Arduino no forma parte de esta versión del repositorio. Por tanto, el significado físico exacto de una lectura alta o baja del sensor de luz depende de cómo el Arduino produzca ese valor. El manual describe la condición implementada en Python sin asumir una conversión no visible en el código disponible.

## 5.3 MQTT

| Parámetro     | Valor                |
| ------------- | -------------------- |
| Broker        | `broker.emqx.io`     |
| Puerto        | `1883`               |
| Identificador | `202500177`          |
| Topic base    | `202500177/edificio` |

## 5.4 Comunicación con Arduino

| Parámetro                              | Valor                       |
| -------------------------------------- | --------------------------- |
| Puerto                                 | `/dev/ttyUSB0`              |
| Baudrate utilizado por `SensorManager` | `9600`                      |
| Datos recibidos                        | `GAS:<entero>,LUZ:<entero>` |

## 5.5 GPIO utilizados por la implementación

La siguiente tabla refleja los valores definidos realmente en `iot/globals.py`.

| Elemento                     | GPIO BCM |
| ---------------------------- | -------: |
| DHT11                        |      `5` |
| HC-SR04 TRIG                 |     `17` |
| HC-SR04 ECHO                 |     `27` |
| Servomotor                   |     `18` |
| Relé de ventilador           |     `11` |
| LED zona 1                   |      `6` |
| LED zona 2                   |     `12` |
| LED zona 3                   |     `13` |
| LED NORMAL                   |     `16` |
| LED ADVERTENCIA              |     `20` |
| LED EMERGENCIA               |     `21` |
| LED indicador de puerta      |     `10` |
| LED indicador de ventilación |      `9` |
| Buzzer                       |     `26` |
| Botón 1                      |     `22` |
| Botón 2                      |     `23` |
| Botón 3                      |     `24` |
| Botón 4                      |     `25` |

El LCD se inicializa mediante I²C con dirección `0x27`, 16 columnas y 2 filas.

> **Verificación recomendada:** el comentario existente junto a `PIN_LED_PUERTA` indica un número físico que no corresponde con el valor BCM `10`. Para cableado físico debe tomarse como autoridad el montaje real y el diagrama de conexiones del equipo; este manual conserva el valor que utiliza el software.

---

# 6. Adquisición de sensores

La clase responsable es [`SensorManager`](../iot/core/sensores.py).

## 6.1 Estrategia general

`SensorManager` conserva dos estructuras importantes:

- `ultimos_valores`: último valor válido de cada sensor;
- `ultima_lectura`: momento en que se actualizó cada sensor.

Esto permite devolver el último valor conocido cuando todavía no corresponde realizar otra lectura o cuando una lectura física falla.

Los tiempos internos configurados en `SensorManager` son:

| Sensor      |                                             Intervalo interno |
| ----------- | ------------------------------------------------------------: |
| Temperatura |                                                           3 s |
| Humedad     |                                                           3 s |
| Gas         | 2 s, aunque su actualización efectiva depende del hilo serial |
| Distancia   |                                                           2 s |
| Luz         | 2 s, aunque su actualización efectiva depende del hilo serial |

`iot/main.py` también tiene sus propios intervalos de solicitud. La combinación significa que `main.py` puede solicitar un dato antes de que `SensorManager` vuelva a consultar físicamente el dispositivo; en ese caso recibe el último valor almacenado.

## 6.2 Temperatura y humedad — DHT11

El DHT11 está configurado en `GPIO5`.

Para temperatura, Python llama al driver `Adafruit_DHT`, redondea el resultado y lo convierte a entero. Si la lectura falla, conserva el último valor válido.

La humedad se obtiene con el mismo sensor y la misma estrategia de tolerancia a fallos.

Las dos variables alimentan el subsistema de monitoreo ambiental y el estado global.

## 6.3 Distancia — HC-SR04

El HC-SR04 utiliza:

- `GPIO17` como `TRIG`;
- `GPIO27` como `ECHO`.

La lectura realiza la secuencia habitual del sensor ultrasónico:

1. asegura `TRIG` en bajo;
2. produce un pulso de aproximadamente `10 μs`;
3. mide la duración del pulso en `ECHO`;
4. calcula la distancia con `duration * 17150`;
5. acepta valores entre `2` y `400 cm`.

Si ocurre un timeout o error, se reutiliza el último valor válido.

## 6.4 Gas y luz — Arduino por serial USB

`SensorManager` abre `/dev/ttyUSB0` y crea un hilo daemon dedicado a leer el puerto serial. Esto evita que el bucle principal tenga que detenerse esperando nuevas líneas del Arduino.

Una línea válida puede tener esta forma:

```text
GAS:315,LUZ:420
```

El método `_procesar_datos_serial()`:

1. divide la línea por `,`;
2. divide cada elemento por `:`;
3. normaliza la clave a mayúsculas;
4. convierte el valor a entero;
5. actualiza la medición de `gas` o `luz`.

`leer_gas()` y `leer_luz()` no vuelven a consultar el puerto: simplemente devuelven el último valor actualizado por el hilo serial.

## 6.5 Publicación de lecturas

En el inicio, `main.py` publica una lectura de cada sensor con `retain=True`. Después continúa publicando con los siguientes intervalos definidos en el bucle principal:

| Sensor      | Intervalo solicitado por `main.py` |
| ----------- | ---------------------------------: |
| Temperatura |                                2 s |
| Humedad     |                                2 s |
| Gas         |                                1 s |
| Distancia   |                              0.5 s |
| Luz         |                                1 s |

Estos intervalos son los de publicación/solicitud del núcleo y no deben confundirse con los intervalos internos de adquisición de `SensorManager`.

---

# 7. Control de actuadores y panel físico

La clase [`ActuadorManager`](../iot/core/actuadores.py) concentra el acceso a los elementos físicos de salida.

## 7.1 Servomotor y puerta

El servo utiliza `GPIO18` con PWM a `50 Hz`.

Los estados lógicos se conservan en `self.puerta_abierta`.

La implementación emplea aproximadamente:

- duty cycle `9.72` para abrir;
- duty cycle `2.5` para cerrar.

Después de posicionar el servo durante `0.5 s`, se coloca el duty cycle en `0`.

`abrir_puerta_temporal()` abre la puerta y crea un `threading.Timer`. El tiempo predeterminado es `5 s`; cuando termina, se invoca el cierre automático.

## 7.2 Iluminación

Las tres zonas se controlan mediante los GPIO `6`, `12` y `13`.

En la implementación actual las tres zonas se manipulan juntas desde `_set_luces()`. Por eso `encender_luces()` y `apagar_luces()` cambian las tres salidas al mismo estado.

El objeto conserva además `modo_luz_auto`, que permite distinguir entre automatización por sensor y control manual.

## 7.3 Ventilación

El ventilador se controla mediante un relé conectado a `GPIO11` y un LED indicador en `GPIO9`.

Al encender:

- se activa el relé;
- `ventilador_encendido` pasa a `True`;
- se enciende el LED indicador.

La clase también conserva `modo_ventilador_auto`.

## 7.4 Alarma

El buzzer se controla por PWM en `GPIO26`.

Los estados relevantes son:

- `alarma_activada`: indica que existe una condición de alarma;
- `buzzer_silenciada`: indica que el usuario ha silenciado el sonido sin eliminar necesariamente la emergencia.

Este detalle es importante: **silenciar el buzzer no equivale a eliminar el estado de emergencia**. El método `silenciar_alarma()` apaga el sonido pero conserva `alarma_activada=True`.

## 7.5 LEDs de estado

Los LEDs representan directamente el estado global:

| Estado      |  GPIO encendido |
| ----------- | --------------: |
| NORMAL      |    `16` — verde |
| ADVERTENCIA | `20` — amarillo |
| EMERGENCIA  |     `21` — rojo |

`_actualizar_leds_estado()` asegura que la salida activa corresponda al estado actual.

## 7.6 LCD

El proyecto intenta utilizar la biblioteca `rpi_lcd`. Si está disponible, inicializa un LCD I²C en `0x27`.

`main.py` rota seis vistas:

1. temperatura y humedad;
2. gas/humo;
3. distancia;
4. luz;
5. puerta;
6. estado global.

Cuando existe ADVERTENCIA o EMERGENCIA, esa información tiene prioridad y reemplaza temporalmente el contenido rotativo normal.

## 7.7 Botones físicos

Los botones usan resistencias `pull-up`, por lo que una pulsación se interpreta cuando el GPIO pasa a nivel bajo. `ActuadorManager` detecta flancos y aplica un debounce temporal de `150 ms`.

| Botón | GPIO | Acción en `main.py`                                                         |
| ----- | ---: | --------------------------------------------------------------------------- |
| 1     | `22` | Abrir/cerrar puerta. Si se abre desde este botón, se usa apertura temporal. |
| 2     | `23` | Alternar modo de iluminación AUTOMÁTICO/MANUAL.                             |
| 3     | `24` | Silenciar alarma.                                                           |
| 4     | `25` | Restablecer alerta si el gas ya no supera el umbral.                        |

---

# 8. Subsistemas de automatización

## 8.1 Monitoreo ambiental

### Propósito

Supervisar temperatura y humedad y responder ante condiciones fuera de los límites configurados.

### Entrada

- temperatura del DHT11;
- humedad del DHT11.

### Reglas implementadas

El estado pasa a ADVERTENCIA cuando:

```text
temperatura > 28
```

o cuando la humedad no se encuentra en:

```text
30 <= humedad <= 70
```

Si la temperatura es alta, el núcleo:

1. coloca el ventilador en modo automático;
2. enciende el ventilador;
3. publica `ON` en el topic del ventilador;
4. registra un evento de advertencia cuando corresponde al cambio de estado.

Si la temperatura deja de ser alta y el ventilador continúa en modo automático, el sistema lo apaga.

La humedad fuera de rango también genera ADVERTENCIA y puede registrar un evento propio.

### Persistencia y visualización

Las mediciones se almacenan periódicamente en `sensor_readings`, se publican por MQTT y el dashboard puede mostrarlas tanto en tiempo real como en historial.

## 8.2 Detección de gas o humo

### Propósito

Detectar la condición crítica de mayor prioridad del sistema.

### Entrada

Valor `gas` recibido desde el Arduino por serial USB.

### Regla implementada

```text
gas > 300
```

produce EMERGENCIA.

Cuando el sistema entra por primera vez en ese estado:

1. activa el buzzer, salvo que esté silenciado;
2. abre la puerta;
3. registra un evento `EMERGENCIA`;
4. publica el estado de la alarma;
5. publica la apertura automática de la puerta.

Mientras el gas siga sobre el umbral, la evaluación global continúa seleccionando EMERGENCIA.

Cuando el valor deja de superar `300`, el núcleo desactiva la alarma, publica `RESTABLECIDA` y puede volver a un estado inferior según temperatura y humedad.

## 8.3 Acceso automatizado

### Entrada

Distancia obtenida mediante HC-SR04.

### Regla automática

```text
distancia < 15 cm
```

Si la puerta se encontraba cerrada:

1. se llama a `abrir_puerta_temporal()`;
2. se registra un evento `PUERTA`;
3. se publica `ABIERTA_AUTO` por MQTT;
4. el temporizador del actuador cierra la puerta después del tiempo configurado.

La puerta también puede manipularse desde el botón físico 1 y desde el dashboard.

## 8.4 Iluminación inteligente

El sistema inicia con `modo_luz_auto=True`.

En modo automático, la implementación actual evalúa:

```python
if luz > UMBRAL_LUZ_BAJA:
    encender_luces()
else:
    apagar_luces()
```

Con el valor configurado, el umbral es `300`.

Cuando cambia el resultado de la automatización, se publica uno de estos estados:

```text
AUTO_ON
AUTO_OFF
```

Desde el dashboard es posible cambiar a modo manual y ordenar encendido o apagado. El botón físico 2 alterna también entre AUTOMÁTICO y MANUAL.

## 8.5 Estado global y alarmas

El estado global no es una variable independiente elegida por el usuario: se recalcula a partir de las lecturas.

La prioridad implementada es:

1. EMERGENCIA por gas;
2. ADVERTENCIA por temperatura o humedad;
3. NORMAL si ninguna condición anterior se cumple.

Los detalles se explican en la siguiente sección.

## 8.6 Panel físico

El panel local permite operar el sistema sin depender del navegador. Combina:

- LCD para supervisión;
- cuatro botones para acciones;
- LEDs de estado;
- LEDs indicadores de actuadores.

Las acciones locales también generan eventos y publicaciones MQTT, de modo que el dashboard pueda reflejar cambios originados físicamente.

---

# 9. Estado global del edificio

## 9.1 NORMAL

Se utiliza cuando:

- `gas <= 300`;
- `temperatura <= 28`;
- `30 <= humedad <= 70`.

En NORMAL:

- el LED verde representa el estado;
- el ventilador se apaga si se encuentra bajo control automático;
- el buzzer no debe permanecer activo.

## 9.2 ADVERTENCIA

Se utiliza cuando no existe emergencia por gas, pero se cumple al menos una de estas condiciones:

- `temperatura > 28`;
- humedad menor a `30`;
- humedad mayor a `70`.

El LED amarillo representa el estado. Cuando la causa es temperatura alta, el ventilador se activa automáticamente.

## 9.3 EMERGENCIA

Tiene prioridad sobre los demás estados y se produce cuando:

```text
gas > 300
```

El LED rojo representa la emergencia. Al entrar en este estado se activan la alarma y la apertura de la puerta.

## 9.4 Propagación de un cambio de estado

Cuando `nuevo_estado` es diferente de `estado_actual`, `main.py`:

1. guarda un documento en `system_status`;
2. registra un evento `CAMBIO_ESTADO`;
3. publica el nuevo valor en MQTT con `retain=True`;
4. actualiza los LEDs y la lógica de alarma mediante `ActuadorManager`;
5. reemplaza `estado_actual`.

El uso de mensajes retenidos permite que un cliente MQTT que se suscriba posteriormente reciba inmediatamente el último estado conservado por el broker para ese topic.

---

# 10. Flujo MQTT

## 10.1 Participantes

El flujo MQTT tiene dos clientes principales visibles en el repositorio:

### Cliente IoT

Creado en `iot/main.py`. Publica sensores y estados y se suscribe a:

```text
202500177/edificio/control/remoto
```

### Cliente del backend

Creado en `backend/app.py`. Se suscribe a:

```text
202500177/edificio/#
```

De esta forma puede escuchar todos los mensajes del edificio.

## 10.2 Topics utilizados

| Topic relativo al base  | Publicador principal | Consumidor principal | Contenido observado                                                                               |
| ----------------------- | -------------------- | -------------------- | ------------------------------------------------------------------------------------------------- |
| `sensores/temperatura`  | Raspberry Pi         | Flask                | Entero de temperatura.                                                                            |
| `sensores/humedad`      | Raspberry Pi         | Flask                | Entero de humedad.                                                                                |
| `sensores/gas`          | Raspberry Pi         | Flask                | Entero recibido desde Arduino.                                                                    |
| `sensores/distancia`    | Raspberry Pi         | Flask                | Distancia en cm.                                                                                  |
| `sensores/luz`          | Raspberry Pi         | Flask                | Entero recibido desde Arduino.                                                                    |
| `actuadores/puerta`     | Raspberry Pi         | Flask                | `ABIERTA`, `CERRADA`, `ABIERTA_AUTO`.                                                             |
| `actuadores/luces`      | Raspberry Pi         | Flask                | `ON`, `OFF`, `AUTO_ON`, `AUTO_OFF`, `MODO_AUTO`, `MODO_MANUAL` y soporte para JSON en el backend. |
| `actuadores/ventilador` | Raspberry Pi         | Flask                | `ON`, `OFF`.                                                                                      |
| `actuadores/alarma`     | Raspberry Pi         | Flask                | `ON`, `OFF`, `SILENCIADA`, `RESTABLECIDA`.                                                        |
| `estado/global`         | Raspberry Pi         | Flask                | `NORMAL`, `ADVERTENCIA`, `EMERGENCIA`.                                                            |
| `control/remoto`        | Flask                | Raspberry Pi         | Comandos de control.                                                                              |
| `arm64/resultados`      | Raspberry Pi         | Flask                | `MAX:n,MIN:n,AVG:n,COUNT:n`.                                                                      |

Todos los anteriores se anteponen con:

```text
202500177/edificio/
```

## 10.3 Lectura de sensor hasta el dashboard

Para una lectura de temperatura, por ejemplo:

1. `main.py` obtiene el valor mediante `SensorManager`.
2. Publica el valor en `202500177/edificio/sensores/temperatura`.
3. EMQX entrega el mensaje al cliente MQTT de Flask.
4. `al_recibir()` reconoce el topic y actualiza `datos["temperatura"]`.
5. El navegador llama a `GET /api/datos`.
6. Flask responde con el diccionario `datos` serializado como JSON.
7. JavaScript modifica el contenido visible del dashboard.

El dashboard no necesita conocer GPIO, drivers ni protocolos de los sensores. Recibe una representación de alto nivel a través de HTTP.

## 10.4 Control remoto desde el dashboard

El dashboard envía objetos JSON con esta forma:

```json
{
  "dispositivo": "puerta",
  "accion": "ABRIR"
}
```

Flask convierte la combinación a un comando textual. Algunos ejemplos son:

| Acción de la interfaz    | Mensaje MQTT generado |
| ------------------------ | --------------------- |
| Puerta / abrir           | `ABRIR_PUERTA`        |
| Puerta / cerrar          | `CERRAR_PUERTA`       |
| Luces / encender         | `ENCENDER_LUCES`      |
| Luces / apagar           | `APAGAR_LUCES`        |
| Iluminación / automático | `MODO_AUTO`           |
| Iluminación / manual     | `MODO_MANUAL`         |
| Alarma / silenciar       | `SILENCIAR_ALARMA`    |
| Sistema / restablecer    | `RESTABLECER_ALERTA`  |

El mensaje se publica en `control/remoto`. `iot/main.py` lo recibe en `on_message()`, ejecuta la acción física, registra el comando en MongoDB y publica el estado correspondiente.

## 10.5 Mensajes retenidos

En varios estados se utiliza `retain=True`. Esto es especialmente visible en:

- estado global;
- puerta;
- luces/modo;
- ventilador;
- alarma;
- último resultado ARM64;
- lecturas iniciales de sensores.

Un mensaje retenido queda asociado al topic en el broker. Cuando un cliente nuevo se suscribe, puede recibir inmediatamente ese último valor, evitando que la interfaz tenga que esperar al siguiente cambio para conocer un estado inicial.

## 10.6 Normalización de datos en Flask

`backend/app.py` traduce ciertos payloads de bajo nivel a términos de interfaz. Por ejemplo:

- `ON` del ventilador se muestra como `ENCENDIDO`;
- `OFF` como `APAGADO`;
- `ABIERTA_AUTO` se representa como `ABIERTA`;
- `RESTABLECIDA` para alarma se traduce a `DESACTIVADA`;
- `AUTO_ON` y `AUTO_OFF` actualizan tanto las zonas como el modo AUTOMÁTICO.

Esta capa de normalización desacopla la representación visual de los mensajes exactos utilizados por la Raspberry Pi.

---

# 11. Modelo de datos en MongoDB Atlas

## 11.1 Base de datos

El nombre utilizado por el código es:

```text
edificio_iot
```

La cadena de conexión se obtiene desde la variable de entorno:

```env
MONGO_URI=...
```

No debe incluirse la cadena real de credenciales en el repositorio. `.gitignore` excluye `.env`.

## 11.2 `sensor_readings`

Almacena una lectura por documento.

Estructura generada por `MongoDBManager`:

```json
{
  "sensor": "temperatura",
  "value": 27,
  "timestamp": "DateTime UTC"
}
```

El campo `sensor` puede utilizar los nombres:

```text
temperatura
humedad
gas
distancia
luz
```

El backend consulta cada sensor por separado y ordena sus documentos por `timestamp`.

## 11.3 `events`

Conserva sucesos importantes del sistema.

```json
{
  "type": "EMERGENCIA",
  "description": "Gas peligroso: 350",
  "timestamp": "DateTime UTC"
}
```

Tipos observados en la implementación incluyen, entre otros:

- `COMANDO`;
- `BOTON`;
- `EMERGENCIA`;
- `ADVERTENCIA`;
- `NORMAL`;
- `CAMBIO_ESTADO`;
- `PUERTA`.

El objetivo de esta colección no es registrar cada ciclo, sino dejar evidencia de acontecimientos relevantes.

## 11.4 `commands`

Cuando `iot/main.py` recibe un comando por MQTT, guarda:

```json
{
  "comando": "ABRIR_PUERTA",
  "timestamp": "DateTime UTC"
}
```

Esto permite que el historial del dashboard muestre las últimas órdenes remotas ejecutadas.

## 11.5 `arm64_results`

Cada ejecución exitosa del módulo ARM64 puede generar:

```json
{
  "maximo": 30,
  "minimo": 24,
  "promedio": 27,
  "cantidad": 20,
  "timestamp": "DateTime UTC"
}
```

El dashboard usa estos documentos para mostrar el historial del procesamiento y construir la gráfica del promedio.

## 11.6 `system_status`

Cada actualización realizada mediante `update_system_status()` inserta un documento nuevo:

```json
{
  "status": "ADVERTENCIA",
  "timestamp": "DateTime UTC"
}
```

En la implementación actual la colección funciona como historial de cambios/inicializaciones de estado, ya que el método utiliza `insert_one()` en lugar de reemplazar un único documento.

## 11.7 Frecuencia de persistencia de sensores

`main.py` incrementa `contador_ciclos` en cada iteración del bucle principal. Cuando alcanza `20`, inserta las cinco lecturas y reinicia el contador.

Esto significa que la persistencia depende del número de iteraciones del bucle principal, no de un temporizador independiente. Los valores insertados son los últimos valores disponibles en ese momento, por lo que pueden repetirse entre documentos si el sensor físico todavía no ha producido una lectura nueva.

## 11.8 Uso del historial en el dashboard

`GET /api/historial?limite=20` consulta:

- hasta `limite` documentos por cada sensor;
- hasta `limite` resultados ARM64;
- los últimos 10 eventos;
- los últimos 10 comandos.

El parámetro `limite` está restringido entre `1` y `100`.

Los resultados de sensores y ARM64 se invierten después de la consulta descendente para entregarlos en orden cronológico a las gráficas.

---

# 12. Backend Flask y dashboard web

## 12.1 Estado actual en memoria

Flask mantiene un diccionario global `datos` con:

- cinco sensores;
- puerta;
- luces;
- ventilador;
- alarma;
- modo de iluminación;
- tres zonas de luz;
- estado global;
- último resultado ARM64;
- contador `ciclo`.

Este diccionario representa **el estado más reciente conocido por el backend**, no el historial completo.

## 12.2 `GET /api/datos`

Devuelve directamente el objeto `datos` como JSON. Es la fuente principal para la vista en tiempo real.

El frontend consulta esta ruta cada `500 ms`.

## 12.3 `GET /api/historial`

Consulta MongoDB Atlas. Si no existe conexión activa, intenta reconectarse antes de responder.

La respuesta exitosa tiene la forma conceptual:

```json
{
  "ok": true,
  "historial": {
    "temperatura": [],
    "humedad": [],
    "gas": [],
    "distancia": [],
    "luz": [],
    "arm64": [],
    "eventos": [],
    "comandos": []
  }
}
```

El navegador ejecuta esta consulta cada `5 s`.

## 12.4 `POST /api/control`

Recibe JSON con `dispositivo` y `accion`, valida que existan y produce el mensaje MQTT que entiende el núcleo IoT.

La ruta no manipula hardware directamente. Su responsabilidad termina al publicar el comando.

## 12.5 Interfaz del dashboard

`backend/templates/index.html` concentra HTML, CSS y JavaScript en un solo archivo. Las vistas principales son:

- Principal;
- Gráficas;
- Control remoto;
- Historial.

El frontend usa **Chart.js** cargado desde CDN.

La vista principal presenta las últimas lecturas, estados de actuadores, estado global y resultado ARM64. Las gráficas cargan datos históricos desde MongoDB y, antes de disponer de historial, el código también puede añadir datos recibidos en tiempo real.

## 12.6 Relación entre MQTT y HTTP

Este proyecto utiliza ambos mecanismos para propósitos diferentes:

- **MQTT** comunica componentes del sistema IoT y transporta eventos/estados en forma asíncrona.
- **HTTP** comunica el navegador con Flask mediante peticiones tradicionales.

Esta separación evita que el navegador tenga que controlar directamente credenciales MQTT, conexiones de hardware o lógica de persistencia.

---

# 13. Módulo de procesamiento ARM64

## 13.1 Objetivo

El módulo ARM64 demuestra procesamiento de bajo nivel sobre datos reales generados por el sistema. Las estadísticas no son calculadas por Python: el programa AArch64 es responsable de obtener:

- máximo;
- mínimo;
- promedio entero;
- cantidad de datos.

Python solamente prepara la entrada, ejecuta el programa, interpreta la salida y distribuye el resultado.

## 13.2 Generación de `datos.txt`

`SensorManager.generar_archivo_arm64(cantidad=20)` crea un archivo con temperaturas enteras y agrega `$` como finalizador.

Ejemplo:

```text
23
25
21
27
$
```

La temperatura ya se convierte a entero al leer el DHT11, por lo que el ensamblador no necesita trabajar con punto flotante.

En `main.py` el procesamiento se solicita cada `10 s` y se generan `20` valores antes de ejecutar el binario.

## 13.3 Integración Python–ARM64

[`iot/arm64_integracion.py`](../iot/arm64_integracion.py) utiliza `platform.machine()` para detectar la arquitectura.

Si la máquina reporta:

```text
aarch64
```

o:

```text
arm64
```

el binario se ejecuta directamente.

En otra arquitectura, la integración intenta utilizar:

```text
qemu-aarch64
```

Esto permite probar un binario ARM64 desde una computadora x86_64 siempre que QEMU esté instalado y pueda ejecutar ese binario.

Antes de cada ejecución se elimina `resultado.txt` anterior. De esta forma, si el programa falla, Python no confunde una salida vieja con un resultado nuevo.

## 13.4 Organización del programa AArch64

El archivo [`iot/arm64_stats.s`](../iot/arm64_stats.s) utiliza estos registros principales:

| Registro | Responsabilidad                                     |
| -------- | --------------------------------------------------- |
| `x23`    | Número que se está construyendo al leer caracteres. |
| `x24`    | Suma acumulada.                                     |
| `x25`    | Cantidad de valores.                                |
| `x26`    | Máximo.                                             |
| `x27`    | Mínimo.                                             |
| `x28`    | Promedio final.                                     |

También reserva:

- `buffer`: 4096 bytes para el contenido de `datos.txt`;
- `num_buffer`: 32 bytes para convertir enteros nuevamente a texto.

## 13.5 Apertura y lectura del archivo

El programa inicia en `_start`; no depende de un `main()` de C.

Utiliza llamadas al sistema de Linux mediante el registro `x8` y la instrucción:

```asm
svc #0
```

Las llamadas observadas son:

| Número en `x8` | Operación utilizada                    |
| -------------: | -------------------------------------- |
|           `56` | Abrir/crear archivo mediante `openat`. |
|           `63` | Leer mediante `read`.                  |
|           `57` | Cerrar mediante `close`.               |
|           `64` | Escribir mediante `write`.             |
|           `93` | Terminar mediante `exit`.              |

El archivo completo se lee en `buffer`, con un máximo de 4096 bytes para esta implementación.

## 13.6 Conversión ASCII a entero

El programa recorre el archivo byte por byte con `ldrb`.

Para cada carácter:

1. comprueba si es `$`;
2. comprueba si es salto de línea;
3. ignora caracteres fuera de `'0'` a `'9'`;
4. convierte un dígito ASCII restando `'0'`;
5. construye el entero mediante la operación `numero = numero * 10 + digito`.

En ensamblador esta última operación se implementa con `madd`:

```asm
madd x23, x23, x10, x9
```

Esto permite procesar valores de más de un dígito sin utilizar funciones de biblioteca de alto nivel.

## 13.7 Acumulación de estadísticas

Al finalizar un número, `save_number`:

1. inicializa máximo y mínimo si es el primer dato;
2. compara el dato con el máximo actual;
3. compara el dato con el mínimo actual;
4. suma el valor a `x24`;
5. incrementa `x25`;
6. limpia el número en construcción.

Cuando se detecta `$`, el programa verifica que exista al menos un dato.

## 13.8 Promedio truncado

El promedio se calcula mediante:

```asm
udiv x28, x24, x25
```

`udiv` realiza división entera sin signo. El resultado descarta cualquier parte fraccionaria, por lo que el promedio queda truncado.

Ejemplo: si la suma es `99` y existen `4` datos, el resultado almacenado es `24`, no `24.75` ni `25`.

## 13.9 Escritura de `resultado.txt`

El programa crea/trunca `resultado.txt` y escribe:

```text
MÁX=<valor>
MIN=<valor>
AVG=<valor>
COUNT=<valor>
```

Para escribir números, la subrutina `write_number` realiza la conversión inversa: divide entre `10`, obtiene residuos y construye los dígitos ASCII desde el final de `num_buffer` hacia atrás.

## 13.10 Lectura del resultado desde Python

`arm64_integracion.py` lee cada línea, separa por `=`, normaliza la clave y devuelve:

```python
{
    "max": ...,
    "min": ...,
    "avg": ...,
    "count": ...
}
```

Después `main.py`:

1. guarda el resultado en `arm64_results`;
2. genera un payload como `MAX:30,MIN:24,AVG:27,COUNT:20`;
3. lo publica en `arm64/resultados` con `retain=True`;
4. Flask lo interpreta;
5. el dashboard muestra el resultado actual y el historial.

## 13.11 Límites visibles de esta implementación

El parser del ensamblador está diseñado para enteros no negativos formados por dígitos ASCII. No existe lógica para signo negativo ni para punto decimal. Esto concuerda con la etapa Python, que genera temperaturas enteras.

Si no aparece `$` antes de llegar al final del contenido leído, el programa termina por la ruta de error. También termina con error si no logró procesar ningún número.

---

# 14. Puesta en marcha

Esta sección describe la puesta en marcha que puede justificarse con los archivos actuales del repositorio.

## 14.1 Requisitos generales

### Backend

`backend/requirements.txt` declara:

```text
flask==3.0.0
paho-mqtt==1.6.1
pymongo==4.6.1
python-dotenv==1.0.0
```

### Raspberry Pi

`iot/requirements.txt` declara:

```text
RPi.GPIO==0.7.1
Adafruit-DHT==1.4.0
paho-mqtt==1.6.1
pymongo==4.6.1
python-dotenv==1.0.0
pyserial==3.5
```

Además, `ActuadorManager` intenta importar `rpi_lcd`, pero esa dependencia no aparece actualmente en `iot/requirements.txt`. Si se utiliza el LCD mediante esa biblioteca, debe estar instalada en el entorno de la Raspberry Pi.

## 14.2 Variable de entorno

Crear un archivo `.env` accesible desde el directorio desde el que se ejecutan los procesos:

```env
MONGO_URI=<cadena-de-conexion-de-mongodb-atlas>
```

El archivo está ignorado por Git y no debe contenerse en el repositorio público.

## 14.3 Backend

Desde `backend/`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

El servidor escucha en:

```text
0.0.0.0:5000
```

Desde la misma máquina puede abrirse normalmente:

```text
http://localhost:5000
```

## 14.4 Núcleo IoT

La ejecución debe realizarse preferiblemente **desde la carpeta `iot/`**:

```bash
cd iot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

Ejecutarlo desde `iot/` es importante en la implementación actual porque `SensorManager.generar_archivo_arm64()` crea `datos.txt` usando una ruta relativa, mientras el programa ARM64 se ejecuta con `iot/` como directorio de trabajo.

## 14.5 Arduino

Antes de iniciar `main.py`, el Arduino debe estar conectado y reconocido en el puerto configurado:

```text
/dev/ttyUSB0
```

El software espera recibir datos a `9600` baudios y con las claves `GAS` y `LUZ`.

Como el firmware no está incluido en el repositorio entregado para este manual, su proceso de carga y configuración debe documentarse cuando ese archivo esté disponible.

## 14.6 MongoDB Atlas

El equipo que ejecuta Flask y la Raspberry Pi necesitan poder usar `MONGO_URI`. Además, la configuración de red de Atlas debe permitir la conexión desde los equipos correspondientes.

## 14.7 ARM64

El repositorio actual ya incluye `iot/arm64_stats`, identificado como un ejecutable ELF AArch64.

En Raspberry Pi ARM64, `arm64_integracion.py` lo ejecuta directamente. En un equipo no ARM64, la integración requiere que `qemu-aarch64` esté disponible.

Esta versión del repositorio **no contiene un `Makefile`**, por lo que el procedimiento exacto de compilación usado por el equipo no puede reconstruirse únicamente a partir de los archivos presentes. El código fuente `.s` y el binario sí están disponibles.

---

# 15. Pruebas y diagnóstico

## 15.1 Filosofía recomendada

Cuando un sistema combina sensores, actuadores, red, base de datos y ensamblador, una falla del sistema completo puede tener muchas causas. La forma más eficiente de diagnosticarlo es comprobar cada capa por separado antes de asumir que el problema se encuentra en la integración.

## 15.2 Pruebas disponibles en `scripts/`

### DHT11

```text
scripts/test_dht11.py
```

Permite verificar temperatura y humedad sin ejecutar el resto del edificio.

### LEDs

```text
scripts/leds_test.py
scripts/test_leds.py
```

Permiten encender y apagar los LEDs de iluminación y estado.

### Buzzer

```text
scripts/test_buzzer.py
```

Comprueba la salida física del buzzer.

### MongoDB

```text
scripts/test_mongo.py
```

Comprueba la conectividad con Atlas e intenta insertar un documento de prueba.

> Este script utiliza un formato de documento de prueba diferente al que utiliza `MongoDBManager` en la aplicación final. Debe entenderse como una prueba de conectividad, no como definición oficial del modelo de datos.

### MQTT

```text
scripts/test_mqtt_pub.py
scripts/test_mqtt_sub.py
```

Uno publica una temperatura simulada y el otro escucha el namespace completo del edificio.

## 15.3 Comprobación de Arduino serial

Si gas o luz permanecen en sus valores iniciales, revisar:

1. que Arduino esté conectado por USB;
2. qué dispositivo creó Linux (`/dev/ttyUSB0`, `/dev/ttyACM0`, etc.);
3. que la ruta coincida con `PUERTO_SERIAL`;
4. que el baudrate sea `9600`;
5. que las líneas tengan el formato esperado.

## 15.4 Comprobación MQTT

Si el dashboard no cambia aunque la Raspberry sí obtiene sensores:

1. verificar conexión a `broker.emqx.io:1883`;
2. ejecutar el suscriptor de prueba;
3. comprobar que aparezcan mensajes bajo `202500177/edificio/#`;
4. revisar la consola de `backend/app.py` para confirmar `[MQTT RECIBIDO]`;
5. comprobar `/api/datos` directamente en el navegador.

## 15.5 Comprobación MongoDB

Si el tiempo real funciona pero no hay historial:

1. verificar `MONGO_URI`;
2. comprobar que Atlas permita la conexión de red;
3. ejecutar `scripts/test_mongo.py`;
4. observar los mensajes `[DB]` del backend;
5. comprobar la respuesta de `/api/historial`.

## 15.6 Comprobación ARM64

Si no aparecen resultados ARM64:

1. ejecutar el núcleo desde `iot/`;
2. verificar que `datos.txt` se genere allí;
3. comprobar que `arm64_stats` exista y tenga permisos de ejecución;
4. en x86_64, comprobar que `qemu-aarch64` esté instalado;
5. ejecutar el binario de forma aislada con un `datos.txt` conocido;
6. verificar si se crea `resultado.txt`;
7. comprobar las cuatro claves esperadas.

---

# 16. Decisiones de diseño

## 16.1 Raspberry Pi como coordinador

La Raspberry Pi concentra las decisiones del edificio porque necesita interactuar tanto con hardware como con servicios de red y el módulo ARM64. Esto evita distribuir reglas críticas entre varios dispositivos con diferentes estados internos.

## 16.2 Arduino como auxiliar de adquisición

Gas y luz llegan por serial desde Arduino. Esta decisión separa la adquisición analógica del control general del edificio y permite que Python trabaje con valores enteros ya digitalizados.

## 16.3 MQTT como desacoplamiento

La Raspberry Pi no necesita conocer detalles de la interfaz web y el backend no necesita acceder a GPIO. Ambos intercambian estados y comandos mediante topics MQTT.

Esto facilita que cada parte pueda probarse de forma independiente: puede publicarse una lectura simulada sin el sensor físico o escucharse el sistema sin abrir el dashboard.

## 16.4 Flask como puente para el navegador

En lugar de conectar JavaScript directamente a MQTT y MongoDB, Flask concentra esas responsabilidades. El frontend utiliza una API HTTP pequeña y sencilla.

## 16.5 Estado actual en memoria e historial en MongoDB

El dashboard tiene dos necesidades distintas:

- saber qué está ocurriendo **ahora**;
- consultar qué ocurrió **antes**.

El diccionario `datos` cubre el primer caso, mientras MongoDB cubre el segundo. Esto evita consultar la base de datos en cada actualización visual de `500 ms`.

## 16.6 Automatización y control manual

El proyecto conserva modos internos para iluminación y ventilación. En particular, una orden manual sobre las luces desactiva el modo automático. Esto evita que el sistema contradiga inmediatamente una acción del usuario por volver a aplicar la regla del sensor en el siguiente ciclo.

## 16.7 ARM64 aislado de Python

El cálculo estadístico se mantiene fuera de Python. La frontera entre ambos módulos son archivos de texto con formatos explícitos. Esto permite demostrar que los cálculos pertenecen realmente al programa AArch64 y facilita probarlo de forma independiente.

## 16.8 Mensajes MQTT retenidos

Los estados importantes se publican frecuentemente con `retain=True`. Esto favorece que un dashboard que se conecta después de iniciado el sistema obtenga estados útiles sin esperar al siguiente evento.

---

# 17. Consideraciones de la implementación actual

Esta sección registra comportamientos y faltantes observables en los archivos actuales. No pretende modificar el diseño; sirve para que una persona nueva no confunda una limitación del repositorio con un error de comprensión del manual.

## 17.1 Firmware de Arduino no incluido

El software de Raspberry Pi demuestra claramente el protocolo serial esperado, pero el código que ejecuta el Arduino no está en el repositorio analizado. No es posible documentar de forma verificable:

- pines utilizados en Arduino;
- modelo exacto de lectura analógica;
- fórmula de conversión de gas;
- fórmula o polaridad de la lectura de luz;
- frecuencia de transmisión del Arduino.

## 17.2 No hay `Makefile` en esta copia

El repositorio contiene `arm64_stats.s` y el ejecutable `arm64_stats`, pero no un `Makefile`. Por esta razón, este manual no presenta como hecho un comando de compilación que no esté registrado en los archivos del proyecto.

## 17.3 Dependencia de LCD

`ActuadorManager` importa `rpi_lcd`, pero `iot/requirements.txt` no la declara. Si el entorno no la tiene instalada, el código continúa funcionando con `LCD_DISPONIBLE=False`, pero el panel LCD queda deshabilitado.

## 17.4 Ruta relativa de `datos.txt`

La generación de `datos.txt` usa una ruta relativa, mientras `arm64_integracion.py` ejecuta el binario dentro de la carpeta `iot`. Para mantener ambos archivos en el mismo directorio, la ejecución habitual debe iniciar `main.py` desde `iot/`.

## 17.5 Muestreo utilizado para ARM64

`generar_archivo_arm64(20)` solicita veinte temperaturas con una pausa de `0.05 s`, mientras `SensorManager` limita la lectura física de temperatura a aproximadamente una cada `3 s`. En consecuencia, un lote de `datos.txt` puede contener valores repetidos porque varias solicitudes reciben la misma lectura almacenada.

## 17.6 Control remoto del ventilador

En `backend/app.py`, tanto la acción visual `ENCENDER` como `APAGAR` del ventilador se traducen actualmente a:

```text
TOGGLE_VENTILADOR
```

Por tanto, el backend no envía órdenes deterministas ON/OFF para este actuador: solicita alternar el estado existente. Este comportamiento debe tenerse presente al depurar la interfaz.

## 17.7 Colección `system_status`

Aunque conceptualmente puede interpretarse como “estado del sistema”, la implementación inserta un documento nuevo cada vez que llama `update_system_status()`. No mantiene un único documento reemplazado, sino una secuencia de estados con timestamp.

---

# 18. Glosario

| Término   | Significado dentro de este proyecto                                                                   |
| --------- | ----------------------------------------------------------------------------------------------------- |
| ADC       | Conversión de una señal analógica a un valor digital; la adquisición de gas/luz se delega al Arduino. |
| AArch64   | Conjunto de instrucciones ARM de 64 bits utilizado por `arm64_stats.s`.                               |
| API       | Conjunto de rutas HTTP que Flask expone al navegador.                                                 |
| Broker    | Servidor intermediario de mensajes MQTT; aquí se utiliza EMQX.                                        |
| BCM       | Esquema de numeración de GPIO utilizado por `RPi.GPIO`.                                               |
| Dashboard | Interfaz web para supervisión, historial y control remoto.                                            |
| GPIO      | Pines digitales de propósito general de la Raspberry Pi.                                              |
| I²C       | Bus utilizado por el LCD en la implementación.                                                        |
| MQTT      | Protocolo de publicación/suscripción que conecta Raspberry Pi y backend.                              |
| Payload   | Contenido de un mensaje MQTT.                                                                         |
| PWM       | Modulación utilizada para controlar servo y buzzer.                                                   |
| `retain`  | Opción MQTT que hace que el broker conserve el último mensaje de un topic.                            |
| Serial    | Comunicación de bytes en secuencia; aquí se utiliza sobre USB entre Arduino y Raspberry Pi.           |
| Topic     | Nombre jerárquico al que se publican mensajes MQTT.                                                   |
| QEMU      | Emulador utilizado por la integración para ejecutar ARM64 en una máquina no ARM64.                    |

---

## Referencia rápida de archivos

| Necesidad                         | Archivo principal                                                 |
| --------------------------------- | ----------------------------------------------------------------- |
| Entender el ciclo completo        | [`iot/main.py`](../iot/main.py)                                   |
| Revisar umbrales y GPIO           | [`iot/globals.py`](../iot/globals.py)                             |
| Entender sensores                 | [`iot/core/sensores.py`](../iot/core/sensores.py)                 |
| Entender actuadores               | [`iot/core/actuadores.py`](../iot/core/actuadores.py)             |
| Entender persistencia             | [`backend/mongo.py`](../backend/mongo.py)                         |
| Entender MQTT del dashboard y API | [`backend/app.py`](../backend/app.py)                             |
| Entender la interfaz              | [`backend/templates/index.html`](../backend/templates/index.html) |
| Entender integración ARM64        | [`iot/arm64_integracion.py`](../iot/arm64_integracion.py)         |
| Entender cálculos AArch64         | [`iot/arm64_stats.s`](../iot/arm64_stats.s)                       |
| Probar módulos aislados           | [`scripts/`](../scripts/)                                         |