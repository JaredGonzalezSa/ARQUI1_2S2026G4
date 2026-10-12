# OptiAula IO

Sistema de apoyo a decisiones que aplica Investigación de Operaciones a datos obtenidos por sensores en aulas y laboratorios.

## Proyecto renovado

OptiAula IO utiliza el prototipo de arquitectura como plataforma de adquisición de datos, pero cambia el propósito central del sistema. Ya no se presenta solamente como un edificio inteligente: transforma lecturas ambientales en modelos de transporte, costo mínimo y programación lineal para apoyar decisiones de compra y asignación energética.

La Raspberry Pi conserva la adquisición física, recibe gas y luz desde Arduino por USB serial y publica las lecturas mediante MQTT. Flask utiliza esos datos como parámetros de modelos de optimización, presenta resultados auditables y mantiene las funciones de monitoreo como soporte del análisis. El sistema funciona con Python y servicios multiplataforma, sin binarios específicos del procesador.

## Problemas que atiende

1. Temperatura elevada durante clases o prácticas.
2. Humedad fuera del rango de confort.
3. Presencia de gas o humo sin alerta temprana.
4. Iluminación encendida cuando no se necesita.
5. Espacios oscuros cuando inicia una actividad.
6. Acceso poco práctico cuando una persona se aproxima.
7. Falta de una vista central del estado del aula.
8. Respuesta tardía ante condiciones de emergencia.
9. Ausencia de historial para justificar mejoras.
10. Dependencia de controles exclusivamente presenciales.

## Mercado objetivo

- Centros educativos con aulas, talleres o laboratorios.
- Academias y centros de capacitación.
- Administradores de espacios de estudio compartidos.
- Instituciones que necesitan un prototipo demostrativo y ampliable antes de una instalación mayor.

## Propuesta de valor

OptiAula IO convierte datos físicos en recomendaciones cuantitativas. Una institución puede comparar proveedores mediante métodos de transporte y asignar un presupuesto energético mediante programación lineal, usando las condiciones reales del aula como entrada. El hardware existente actúa como fuente de datos y mecanismo de demostración; la aportación nueva es el sistema de optimización y apoyo a decisiones.

## Funciones principales

| Área | Función |
| --- | --- |
| Ambiente | Lee temperatura y humedad con DHT11 y controla la ventilación. |
| Seguridad | Detecta gas o humo, activa alarma, señaliza el estado y abre la puerta durante una emergencia. |
| Acceso | Usa el HC-SR04 y el servomotor para apertura por proximidad o por orden manual. |
| Iluminación | Controla tres zonas en modo automático o manual. |
| Supervisión | Publica lecturas y estados por MQTT, conserva historial y muestra un dashboard web. |
| Operación local | Ofrece LCD y cuatro botones para acciones esenciales sin depender del navegador. |
| Registro académico | Permite registrar estudiantes por nombre y carné desde el dashboard. |
| Optimización de compras | Compara Esquina Noroeste, Costo Mínimo, Vogel y una solución óptima para distribuir compras. |
| Programación lineal | Asigna un presupuesto energético entre ventilación y tres zonas de iluminación usando datos de sensores. |

## Arquitectura

```text
DHT11 + HC-SR04 ─┐
Arduino (gas/luz) ├─> Raspberry Pi + Python ─> actuadores y LCD
Botones físicos ──┘             │
                                ├─> MQTT/EMQX ─> Flask/dashboard
                                └─> MongoDB Atlas
```

El navegador nunca accede directamente a GPIO. Los comandos siguen la ruta navegador, Flask, MQTT y Raspberry Pi.

El módulo administrativo utiliza `GET /api/estudiantes` y `POST /api/estudiantes`. Los registros se almacenan en la colección `students` de MongoDB Atlas y el carné se protege con un índice único.

El módulo **Costo mínimo** recibe proveedores, productos o destinos, costos unitarios, oferta y demanda. `POST /api/optimizacion/transporte` permite ejecutar un método o comparar los cuatro. Si la oferta total difiere de la demanda, el backend agrega automáticamente una fila o columna ficticia de costo cero. Los cálculos no se almacenan ni interactúan con MQTT o GPIO.

El módulo **Programación lineal** usa las últimas lecturas MQTT de temperatura, humedad, gas, luz y distancia. `POST /api/optimizacion/recursos` maximiza el beneficio de confort y seguridad sujeto a un presupuesto energético. La solución es exacta para este modelo de mochila fraccionaria y se actualiza cada diez segundos mientras la vista está abierta. Es una recomendación: nunca envía comandos a los actuadores.

## Conexiones físicas preservadas

No se cambió ningún pin, dirección I2C ni puerto serial del proyecto base.

| Componente | Configuración original |
| --- | --- |
| DHT11 | GPIO5, pin físico 29 |
| HC-SR04 TRIG | GPIO17, pin físico 11 |
| HC-SR04 ECHO | GPIO27, pin físico 13 |
| Servomotor | GPIO18, pin físico 12 |
| Relé de ventilador | GPIO11, pin físico 23 |
| LEDs de iluminación | GPIO6, GPIO12 y GPIO13 |
| LEDs de estado | GPIO16, GPIO20 y GPIO21 |
| LED de puerta | GPIO10 |
| LED de ventilación | GPIO9 |
| Buzzer | GPIO26, pin físico 37 |
| Botones | GPIO22, GPIO23, GPIO24 y GPIO25 |
| LCD | I2C `0x27`, 16 x 2 |
| Arduino | `/dev/ttyUSB0` por USB serial |

La fuente de verdad para estos valores permanece en [`iot/globals.py`](iot/globals.py).

## Estructura

```text
Proyecto 1/
├── backend/
│   ├── app.py
│   ├── mongo.py
│   ├── linear_optimizer.py
│   ├── transport.py
│   ├── requirements.txt
│   ├── static/
│   └── templates/index.html
├── docs/
│   ├── manual-tecnico.md
│   ├── propuesta-fase-1.md
│   └── img/
├── iot/
│   ├── core/actuadores.py
│   ├── core/sensores.py
│   ├── globals.py
│   ├── limpiar_retain.py
│   ├── main.py
│   └── requirements.txt
└── scripts/
```

## Puesta en marcha

### Configuración única

Antes del primer arranque, copie `backend/.env.example` como `backend/.env` y
reemplace la URI de ejemplo con la conexión real de MongoDB Atlas. El archivo
`.env` está ignorado por Git y sirve tanto al backend como al núcleo IoT.

En Raspberry Pi solo se requiere una vez:

```bash
sudo apt install python-is-python3 python3-venv
```

### Backend

```bash
cd "Proyecto 1/backend"
python app.py
```

El dashboard queda disponible en `http://localhost:5000`. En la primera
ejecución, `bootstrap.py` crea `backend/.venv`, instala las dependencias y
reinicia el programa dentro de ese entorno. Las siguientes ejecuciones arrancan
directamente. Si cambia `backend/requirements.txt`, las dependencias se
sincronizan automáticamente.

### Núcleo IoT

```bash
cd "Proyecto 1/iot"
python main.py
```

El núcleo IoT prepara de la misma forma su propio entorno en `iot/.venv`, sin
mezclar sus dependencias con las del backend. Se necesita configurar una vez
una variable `MONGO_URI` válida (o un archivo `.env` local) y tener acceso al
broker MQTT configurado en `iot/globals.py`.


## Entregables de Fase 1

- [Propuesta desarrollada](docs/propuesta-fase-1.md)
- Presentación de cinco diapositivas en `docs/fase-1-aulanexo.pptx`
- Logotipo en `docs/img/aulanexo-logo.png`

## Alcance técnico

La migración retiró el módulo de procesamiento específico del proyecto anterior, sus archivos intermedios, tema MQTT, colección de resultados, parser, vistas y gráficas asociadas. Sensores, actuadores, automatización, MQTT, MongoDB y dashboard continúan como subsistemas independientes. El registro de estudiantes y la optimización de compras se añadieron como funciones administrativas separadas y no modifican el control físico.
