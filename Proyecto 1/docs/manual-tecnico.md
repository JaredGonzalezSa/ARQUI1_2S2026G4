# Manual técnico de OptiAula IO

## 1. Propósito

OptiAula IO es un sistema de apoyo a decisiones basado en Investigación de Operaciones. Reutiliza la adquisición de sensores y los actuadores de una Raspberry Pi, e integra mensajería MQTT, persistencia en MongoDB Atlas, optimización matemática y un dashboard Flask.

## 2. Componentes

| Componente | Responsabilidad |
| --- | --- |
| Raspberry Pi | Ejecuta la lógica, lee GPIO, controla actuadores y se comunica con servicios externos. |
| Arduino | Envía lecturas de gas y luz por USB serial. |
| `iot/main.py` | Coordina adquisición, automatización, MQTT y persistencia. |
| `SensorManager` | Lee temperatura, humedad, distancia, gas y luz. |
| `ActuadorManager` | Controla puerta, luces, ventilador, buzzer, LEDs, LCD y botones. |
| EMQX | Intermedia mensajes entre el núcleo IoT y Flask. |
| MongoDB Atlas | Conserva lecturas, eventos, comandos, estudiantes y estados globales. |
| Flask | Sirve el dashboard, recibe MQTT y expone la API HTTP. |

## 3. Conexiones físicas

La migración conserva sin cambios la configuración de `iot/globals.py`.

| Componente | GPIO o interfaz |
| --- | --- |
| DHT11 | GPIO5 |
| HC-SR04 TRIG | GPIO17 |
| HC-SR04 ECHO | GPIO27 |
| Servomotor | GPIO18 |
| Relé de ventilador | GPIO11 |
| LEDs de iluminación | GPIO6, GPIO12 y GPIO13 |
| LEDs de estado | GPIO16, GPIO20 y GPIO21 |
| LED de puerta | GPIO10 |
| LED de ventilación | GPIO9 |
| Buzzer | GPIO26 |
| Botones | GPIO22, GPIO23, GPIO24 y GPIO25 |
| LCD | I2C `0x27`, 16 columnas y 2 filas |
| Arduino | USB serial `/dev/ttyUSB0` |

## 4. Estados y automatización

- `NORMAL`: no existe una condición crítica.
- `ADVERTENCIA`: temperatura o humedad requieren atención.
- `EMERGENCIA`: el nivel de gas supera el umbral configurado.

La ventilación responde a la temperatura, la iluminación responde al nivel de luz cuando opera en modo automático y la puerta puede abrirse por proximidad. Ante gas peligroso, el sistema activa la alarma y señalización de emergencia.

## 5. Flujo de datos

```text
Sensores -> SensorManager -> main.py -> MQTT -> Flask -> navegador
                              |
                              +-> MongoDB Atlas
Comando web -> Flask -> MQTT -> main.py -> ActuadorManager -> hardware
```

## 6. Temas MQTT

El prefijo actual es `202500177/edificio` para mantener compatibilidad con la instalación existente.

| Tema relativo | Contenido |
| --- | --- |
| `sensores/temperatura` | Grados Celsius. |
| `sensores/humedad` | Porcentaje. |
| `sensores/gas` | Lectura del sensor. |
| `sensores/distancia` | Centímetros. |
| `sensores/luz` | Lectura del LDR. |
| `actuadores/puerta` | Estado de la puerta. |
| `actuadores/luces` | Estado y modo de iluminación. |
| `actuadores/ventilador` | `ON` u `OFF`. |
| `actuadores/alarma` | Estado de alarma. |
| `estado/global` | `NORMAL`, `ADVERTENCIA` o `EMERGENCIA`. |
| `control/remoto` | Orden enviada desde el dashboard. |

## 7. MongoDB Atlas

La base `edificio_iot` conserva compatibilidad con los datos existentes.

| Colección | Uso |
| --- | --- |
| `sensor_readings` | Lecturas históricas. |
| `events` | Alertas y acciones relevantes. |
| `commands` | Órdenes remotas. |
| `system_status` | Cambios de estado global. |
| `students` | Nombre, carné único y fecha de registro de cada estudiante. |

## 8. API del dashboard

- `GET /`: interfaz principal.
- `GET /api/datos`: último estado recibido por MQTT.
- `GET /api/historial?limite=20`: lecturas, eventos y comandos.
- `POST /api/control`: convierte una acción web en una orden MQTT.
- `GET /api/estudiantes`: devuelve hasta 200 estudiantes, comenzando por los más recientes.
- `POST /api/estudiantes`: valida y registra un estudiante; rechaza carnés duplicados.
- `POST /api/optimizacion/transporte`: valida y resuelve una matriz de transporte con un método individual o en modo comparación.
- `POST /api/optimizacion/recursos`: usa las lecturas MQTT actuales y un presupuesto para resolver la asignación lineal de energía.

## 9. Registro administrativo de estudiantes

La vista **Estudiantes** del dashboard contiene un formulario con nombre completo y carné. El backend normaliza espacios, convierte el carné a mayúsculas y valida longitudes antes de guardar. MongoDB mantiene un índice único sobre `carnet`, por lo que un mismo carné no puede registrarse dos veces.

Esta vista todavía no implementa autenticación. Cualquier persona con acceso al dashboard puede abrirla; antes de exponer el sistema fuera de una red controlada se debe añadir inicio de sesión y autorización administrativa.

## 10. Módulo de costo mínimo

La vista **Costo mínimo** modela compras o distribución como un problema de transporte. Cada fila representa un proveedor con oferta disponible; cada columna representa un producto, sede o destino con demanda; cada celda contiene el costo unitario correspondiente.

Métodos disponibles:

- **Esquina Noroeste:** construye una solución factible siguiendo el orden de la matriz; no considera costos al elegir.
- **Costo Mínimo:** asigna primero en las celdas de menor costo.
- **Aproximación de Vogel:** usa penalizaciones por fila y columna para construir una solución inicial generalmente competitiva.
- **Óptimo por flujo de costo mínimo:** obtiene el costo total mínimo exacto para cantidades enteras.
- **Comparar todos:** muestra el costo de cada estrategia y la matriz de la solución óptima.

El navegador admite matrices de 2 x 2 a 6 x 6; la API acepta hasta 20 x 20. Los costos deben ser números finitos no negativos y las ofertas y demandas deben ser enteros no negativos. Si los totales no coinciden, se agrega un proveedor o destino ficticio con costo cero y la respuesta informa el ajuste. Esquina Noroeste, Costo Mínimo y Vogel son heurísticas de solución inicial, por lo que no garantizan por sí solas el costo óptimo.

El cálculo se ejecuta en `backend/transport.py`, no requiere MongoDB y permanece aislado de MQTT, sensores y actuadores.

## 11. Programación lineal basada en sensores

La vista **Programación lineal** convierte las lecturas actuales en cotas de demanda para cuatro variables continuas:

- `ventilacion`: porcentaje recomendado de ventilación, limitado por temperatura, humedad y gas.
- `luz_zona1`, `luz_zona2` y `luz_zona3`: porcentajes recomendados de iluminación, limitados por el LDR. La proximidad aumenta la prioridad de la zona 1.

El modelo maximiza `Z = suma(beneficio_i * x_i)`, sujeto a `suma(costo_i * x_i) <= presupuesto` y `0 <= x_i <= demanda_i`. Su estructura corresponde a una mochila fraccionaria, por lo que ordenar las variables según su beneficio marginal por unidad energética entrega la solución óptima. El presupuesto se expresa en unidades normalizadas de 0 a 315.

Cuando el gas supera 300, su contribución a la función objetivo hace que la ventilación tenga prioridad y la interfaz muestra una advertencia. Esta recomendación no reemplaza la lógica de emergencia existente. La API no publica MQTT ni acciona GPIO; el operador conserva la decisión final.

El cálculo se implementa en `backend/linear_optimizer.py`. La vista actualiza el plan cada diez segundos usando las lecturas más recientes recibidas por Flask.

## 12. Puesta en marcha

1. Instalar una sola vez Python con soporte para entornos virtuales. En Raspberry Pi: `sudo apt install python-is-python3 python3-venv`.
2. Definir `MONGO_URI` en el entorno o en un archivo `.env` local que no se publique en Git.
3. Verificar el Arduino en `/dev/ttyUSB0` y el LCD en `0x27`.
4. Desde `backend`, ejecutar únicamente `python app.py`.
5. Desde `iot`, ejecutar únicamente `python main.py`.
6. Abrir `http://localhost:5000`.

`bootstrap.py` detecta cada archivo `requirements.txt`, crea un `.venv` separado
para el componente, instala las dependencias en la primera ejecución y vuelve a
iniciar el mismo programa con el intérprete correcto. Un hash dentro del entorno
evita reinstalar en cada arranque y permite actualizar automáticamente cuando
cambian las dependencias. La preparación no altera MQTT, GPIO, sensores,
actuadores ni la lógica de optimización.

## 13. Pruebas recomendadas

- Ejecutar los scripts individuales de DHT11, buzzer, LEDs y LCD.
- Confirmar publicación y suscripción MQTT.
- Confirmar escritura y consulta de MongoDB.
- Probar puerta, iluminación, ventilador y alarma desde el panel físico y el dashboard.
- Simular los estados `NORMAL`, `ADVERTENCIA` y `EMERGENCIA` de manera controlada.
- Registrar un estudiante, comprobar que aparece en la lista y verificar que un carné repetido devuelve un conflicto.
- Cargar el ejemplo de transporte, comparar los cuatro métodos y verificar que cada suma de fila y columna respeta oferta y demanda.
- Probar un caso no balanceado y confirmar que la respuesta informa el proveedor o destino ficticio.
- Variar temperatura, humedad, gas, luz y presupuesto para comprobar que la asignación nunca excede la demanda ni la energía disponible.
- Superar el umbral de gas de forma simulada y confirmar que el modelo prioriza ventilación y muestra la advertencia de emergencia.

## 14. Límites del prototipo

Los sensores de bajo costo requieren calibración y no sustituyen dispositivos certificados. Una instalación real necesita gabinete, protección eléctrica, evaluación de cargas, red confiable y procedimientos de mantenimiento.
