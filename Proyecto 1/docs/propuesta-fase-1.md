# Fase 1 - OptiAula IO

## 1. Nombre del producto o servicio

**OptiAula IO** es un sistema de apoyo a decisiones que aplica modelos de transporte y programación lineal a datos ambientales capturados en aulas y laboratorios.

El prototipo conserva la electrónica del proyecto base como plataforma de captura y demostración, pero cambia su objetivo: utiliza las lecturas para recomendar cómo asignar recursos limitados, reducir costos y comparar decisiones mediante métodos de Investigación de Operaciones.

## 2. Problemas que resuelve

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

Para la encuesta indicada en los lineamientos, cada participante debe elegir solo uno de estos diez problemas. La prioridad final y el diagrama de Pareto se elaborarán con resultados reales de por lo menos 20 respuestas. No se inventan resultados en esta fase.

## 3. Mercado objetivo

### Usuarios directos

- Docentes y estudiantes que ocupan aulas, talleres y laboratorios.
- Encargados de laboratorio y personal de mantenimiento.
- Administradores que necesitan conocer incidentes y condiciones del espacio.

### Clientes potenciales

- Colegios, institutos, universidades y academias.
- Centros de capacitación con espacios cerrados de uso recurrente.
- Instituciones que quieren validar un aula inteligente mediante un prototipo antes de ampliar la instalación.

### Propuesta de valor

OptiAula IO integra adquisición de datos, optimización de compras y planificación energética. El sistema ayuda a distribuir adquisiciones entre proveedores y convierte temperatura, humedad, gas, luz y proximidad en parámetros de un modelo lineal. Así, la institución obtiene recomendaciones cuantitativas y comparables en lugar de limitarse a observar o automatizar dispositivos.

## 4. Limitaciones y recursos disponibles

### Recursos

- Raspberry Pi como controlador principal.
- Arduino para adquisición serial de gas y luz.
- DHT11, HC-SR04, sensor de gas y LDR.
- Servomotor, relé y ventilador, buzzer, LEDs, LCD y cuatro botones.
- Python, Flask, MQTT con EMQX y MongoDB Atlas.
- Dashboard web y scripts de prueba ya funcionales.
- Maqueta física disponible para demostrar el prototipo.

### Limitaciones

- El DHT11 y los sensores económicos no sustituyen instrumentos certificados.
- El prototipo depende de energía, red y acceso al broker para funciones remotas.
- MongoDB Atlas y el broker externo requieren conectividad.
- La maqueta valida el concepto, pero una instalación real exige protecciones eléctricas, gabinete, calibración y evaluación de seguridad.
- El costo final depende del número de aulas y actuadores por zona.
- La disponibilidad comercial del nombre y logotipo debe validarse antes de registrar la marca.

### Factibilidad inicial

El prototipo es fabricable porque reutiliza componentes existentes y una integración ya operativa. La oferta puede estructurarse como kit por aula más instalación y mantenimiento. La factibilidad financiera y comercial definitiva requiere cotizaciones actuales, encuesta y validación con clientes, por lo que no se presentan cifras inventadas.

## 5. Nombre y logo

**Nombre:** OptiAula IO

**Concepto visual:** una puerta de aula conectada con una hoja y una señal inalámbrica. La puerta representa acceso, la hoja representa confort y eficiencia, y la señal representa monitoreo IoT.

**Paleta:** azul marino para confianza técnica, turquesa para ambiente y ámbar para alertas.

El logotipo se encuentra en [`img/aulanexo-logo.png`](img/aulanexo-logo.png).

## Innovación y relación con el proyecto base

La renovación no se limita a cambiar el nombre. El nuevo enfoque define un cliente, un espacio de uso, diez problemas medibles y una ruta de validación comercial. Se conserva la arquitectura comprobada como referencia técnica y se reconstruyen la narrativa, la experiencia del dashboard y los entregables alrededor del aula inteligente.

La declaración de “80% idea nueva + 20% benchmarking” se tratará como meta de diseño. Para sostenerla en el informe final, el grupo deberá documentar qué funciones provienen de referencias comparables y cuáles fueron diseñadas por el equipo.

### Módulo de costo mínimo

La nueva vista del dashboard permite registrar una matriz de costos por proveedor y producto o destino, junto con la oferta y demanda. El usuario puede aplicar Esquina Noroeste, Costo Mínimo, Aproximación de Vogel o un algoritmo exacto de flujo de costo mínimo, además de comparar sus costos totales. Esta función traslada al prototipo los métodos de transporte y asignación de recursos estudiados en Investigación de Operaciones.

Las tres primeras alternativas producen soluciones iniciales factibles y se presentan como heurísticas; la opción de flujo de costo mínimo es la que garantiza el óptimo para cantidades enteras. El balanceo automático mediante un proveedor o destino ficticio permite trabajar con casos donde oferta y demanda no son iguales. El módulo es exclusivamente administrativo y no modifica el cableado, la adquisición de sensores ni el control de actuadores.

### Programación lineal con datos reales

Las lecturas MQTT alimentan un modelo continuo con cuatro variables: ventilación y nivel recomendado para tres zonas de iluminación. La función objetivo maximiza el beneficio de confort y seguridad, mientras una restricción limita el consumo al presupuesto energético seleccionado por el usuario. La temperatura, humedad y gas determinan la demanda máxima de ventilación; el nivel de luz determina la demanda de iluminación; y la distancia modifica la prioridad de la primera zona.

Este componente convierte el hardware heredado en una fuente de parámetros para Investigación de Operaciones. El resultado muestra asignación, cobertura, energía utilizada, demanda pendiente y beneficio total. Se mantiene separado de los actuadores: funciona como apoyo a la decisión y no como control automático.

## Conexiones preservadas

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

La configuración se mantiene en `iot/globals.py` y no debe duplicarse en el código.

## Arquitectura funcional portable

```text
Sensores y botones -> Raspberry Pi/Python -> actuadores y LCD
                              |
                              +-> MQTT/EMQX -> Flask/dashboard
                              |
                              +-> MongoDB Atlas
```


## Evidencia requerida para las siguientes etapas

- Encuesta de al menos 20 personas, una selección por persona.
- Tabla de frecuencias y porcentaje acumulado.
- Diagrama de Pareto con datos reales.
- Un Ishikawa por cada causa incluida en el tramo acumulado cercano al 80%.
- Estudio de tiempos predeterminados sobre el proceso de armado o instalación definido por el grupo.
- Video final de cinco minutos con todos los integrantes y demostración del prototipo.
