# AulaNexo

Sistema IoT para seguridad ambiental, confort, acceso e iluminación eficiente en aulas y laboratorios.

## Propuesta renovada

AulaNexo adapta el prototipo de edificio inteligente a una necesidad concreta: administrar espacios educativos que suelen operar sin información ambiental, alertas tempranas ni automatización accesible. La solución conserva el hardware y el cableado original, pero reorganiza la experiencia alrededor de docentes, estudiantes, encargados de laboratorio y administradores.

La Raspberry Pi coordina sensores y actuadores, recibe gas y luz desde Arduino por USB serial, publica datos mediante MQTT, almacena historial en MongoDB Atlas y permite supervisión y control desde un dashboard Flask. El sistema funciona con Python y servicios multiplataforma, sin binarios específicos del procesador.

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

AulaNexo integra monitoreo, automatización y control remoto en un prototipo reutilizable. Un solo sistema muestra temperatura, humedad, gas, luz y proximidad, y responde mediante ventilación, iluminación, alarma y apertura de puerta. La institución puede probar la solución a pequeña escala antes de decidir una implementación por aula.

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

### Backend

```bash
cd "Proyecto 1/backend"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

El dashboard queda disponible en `http://localhost:5000`.

### Núcleo IoT

```bash
cd "Proyecto 1/iot"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

Se necesita una variable `MONGO_URI` válida y acceso al broker MQTT configurado en `iot/globals.py`.

## Entregables de Fase 1

- [Propuesta desarrollada](docs/propuesta-fase-1.md)
- Presentación de cinco diapositivas en `docs/fase-1-aulanexo.pptx`
- Logotipo en `docs/img/aulanexo-logo.png`

## Alcance técnico

La migración retiró el módulo de procesamiento específico del proyecto anterior, sus archivos intermedios, tema MQTT, colección de resultados, parser, vistas y gráficas asociadas. Sensores, actuadores, automatización, MQTT, MongoDB y dashboard continúan como subsistemas independientes. El registro de estudiantes y la optimización de compras se añadieron como funciones administrativas separadas y no modifican el control físico.
