import json
import os
import re

from flask import Flask, jsonify, render_template, request
import paho.mqtt.client as mqtt

from datetime import datetime, timezone
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

from mongo import MongoDBManager
from linear_optimizer import LinearOptimizationError, optimize_sensor_resources
from transport import METHOD_NAMES, TransportValidationError, solve_transport
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from iot import globals as gl

# -------------------------------------------------
# CONFIGURACIÓN
# -------------------------------------------------

app = Flask(__name__)

BROKER = "broker.emqx.io"
PORT = 1883
BASE = "202500177/edificio"


# -------------------------------------------------
# DATOS ACTUALES
# -------------------------------------------------

datos = {
    "temperatura": 0,
    "humedad": 0,
    "gas": 0,
    "distancia": 0,
    "luz": 0,

    "puerta": "---",
    "luces": "---",
    "ventilador": "---",
    "alarma": "---",

    "modo_iluminacion": "---",
    "zona1": "---",
    "zona2": "---",
    "zona3": "---",

    "estado": "---",
    "ciclo": 0
}


# -------------------------------------------------
# MONGODB
# -------------------------------------------------

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

mongo_client = None
mongo_db = None


def conectar_mongo():

    global mongo_client
    global mongo_db

    if not MONGO_URI:

        print(
            "[DB] MONGO_URI no encontrada."
        )

        return False

    try:

        mongo_client = MongoClient(
            MONGO_URI,
            serverSelectionTimeoutMS=30000,
            connectTimeoutMS=10000
        )

        mongo_client.admin.command(
            "ping"
        )

        mongo_db = mongo_client[
            "edificio_iot"
        ]

        mongo_db["students"].create_index(
            "carnet",
            unique=True
        )

        print(
            "[DB] Conectado a MongoDB Atlas"
        )

        return True

    except Exception as error:

        mongo_db = None

        print(
            "[DB] No se pudo conectar:",
            error
        )

        return False


conectar_mongo()


# -------------------------------------------------
# CONVERTIR TIMESTAMP
# -------------------------------------------------

def convertir_timestamp(timestamp):

    if timestamp is None:
        return ""

    if timestamp.tzinfo is None:

        timestamp = timestamp.replace(
            tzinfo=timezone.utc
        )

    return timestamp.isoformat()


# -------------------------------------------------
# MQTT
# -------------------------------------------------

def al_conectar(
    client,
    userdata,
    flags,
    reason_code,
    properties
):

    if reason_code == 0:

        print(
            "[MQTT] Conectado a EMQX"
        )

        topic = f"{BASE}/#"

        client.subscribe(
            topic
        )

        print(
            "[MQTT] Escuchando:",
            topic
        )

    else:

        print(
            "[MQTT] Error de conexión:",
            reason_code
        )

def normalizar_modo(valor):
    """Normaliza el modo de iluminación a AUTOMATICO o MANUAL."""
    v = str(valor).strip().upper()
    if v in ("AUTO", "AUTOMATICO", "AUTOMÁTICO", "AUTO_ON", "AUTO_OFF"):
        return "AUTOMATICO"
    if v in ("MANUAL", "MAN"):
        return "MANUAL"
    return v


def normalizar_zona(valor):
    """Normaliza el estado de una zona a ENCENDIDA o APAGADA."""
    v = str(valor).strip().upper()
    if v in ("ON", "ENCENDIDA", "ENCENDIDO", "TRUE", "1"):
        return "ENCENDIDA"
    if v in ("OFF", "APAGADA", "APAGADO", "FALSE", "0"):
        return "APAGADA"
    return v


def derivar_estado_global_luces():
    """Deriva el estado global: ENCENDIDAS solo si las 3 zonas están encendidas.
    En cualquier otro caso → APAGADAS (nunca PARCIAL)."""
    zonas = [datos["zona1"], datos["zona2"], datos["zona3"]]
    if all(z == "ENCENDIDA" for z in zonas):
        return "ENCENDIDAS"
    return "APAGADAS"


def al_recibir(
    client,
    userdata,
    mensaje
):

    topic = mensaje.topic
    contenido = mensaje.payload.decode("utf-8")

    print(f"[MQTT RECIBIDO] {topic} -> {contenido}") 

    # ------------------------------------------
    # SENSORES
    # ------------------------------------------

    if topic == f"{BASE}/sensores/temperatura":
        datos["temperatura"] = contenido

    elif topic == f"{BASE}/sensores/humedad":
        datos["humedad"] = contenido

    elif topic == f"{BASE}/sensores/gas":
        datos["gas"] = contenido

    elif topic == f"{BASE}/sensores/distancia":
        datos["distancia"] = contenido

    elif topic == f"{BASE}/sensores/luz":
        datos["luz"] = contenido
        datos["ciclo"] += 1

    # ------------------------------------------
    # ACTUADORES
    # ------------------------------------------

    elif topic == f"{BASE}/actuadores/puerta":
        # Valores esperados: "ABIERTA", "CERRADA", "ABIERTA_AUTO"
        if contenido == "ABIERTA" or contenido == "ABIERTA_AUTO":
            datos["puerta"] = "ABIERTA"
        else:
            datos["puerta"] = contenido

    elif topic == f"{BASE}/actuadores/luces":
        try:
            estado_luces = json.loads(contenido)
            if "modo" in estado_luces:
                modo = str(estado_luces["modo"]).strip().upper()
                if modo in ("AUTO", "AUTOMATICO", "AUTOMÁTICO"):
                    datos["modo_iluminacion"] = "AUTOMATICO"
                elif modo == "MANUAL":
                    datos["modo_iluminacion"] = "MANUAL"
            for zona in ("zona1", "zona2", "zona3"):
                if zona in estado_luces:
                    v = str(estado_luces[zona]).strip().upper()
                    datos[zona] = "ENCENDIDA" if v in ("ON", "ENCENDIDA", "ENCENDIDO") else "APAGADA"
        except (json.JSONDecodeError, TypeError):
            texto = contenido.strip().upper()

            if texto in ("ON", "ENCENDIDA", "ENCENDIDAS"):
                datos["zona1"] = datos["zona2"] = datos["zona3"] = "ENCENDIDA"

            elif texto in ("OFF", "APAGADA", "APAGADAS"):
                datos["zona1"] = datos["zona2"] = datos["zona3"] = "APAGADA"

            elif texto == "AUTO_ON":
                datos["zona1"] = datos["zona2"] = datos["zona3"] = "ENCENDIDA"
                datos["modo_iluminacion"] = "AUTOMATICO"

            elif texto == "AUTO_OFF":
                datos["zona1"] = datos["zona2"] = datos["zona3"] = "APAGADA"
                datos["modo_iluminacion"] = "AUTOMATICO"

            elif texto == "MODO_AUTO":
                datos["modo_iluminacion"] = "AUTOMATICO"

            elif texto == "MODO_MANUAL":
                datos["modo_iluminacion"] = "MANUAL"

            else:
                datos["luces"] = texto

        # Derivar estado global (nunca PARCIAL)
        zonas = [datos["zona1"], datos["zona2"], datos["zona3"]]
        datos["luces"] = "ENCENDIDAS" if all(z == "ENCENDIDA" for z in zonas) else "APAGADAS"

    elif topic == f"{BASE}/actuadores/ventilador":
        # "ON" o "OFF"
        if contenido == "ON":
            datos["ventilador"] = "ENCENDIDO"
        elif contenido == "OFF":
            datos["ventilador"] = "APAGADO"
        else:
            datos["ventilador"] = contenido

    elif topic == f"{BASE}/actuadores/alarma":
        # "ON", "OFF", "SILENCIADA", "RESTABLECIDA"
        if contenido == "ON":
            datos["alarma"] = "ACTIVADA"
        elif contenido == "OFF" or contenido == "RESTABLECIDA":
            datos["alarma"] = "DESACTIVADA"
        elif contenido == "SILENCIADA":
            datos["alarma"] = "SILENCIADA"
        else:
            datos["alarma"] = contenido

    # ------------------------------------------
    # ESTADO GLOBAL
    # ------------------------------------------

    elif topic == f"{BASE}/estado/global":
        datos["estado"] = contenido

cliente_mqtt = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="Dashboard_202500177"
)

cliente_mqtt.on_connect = al_conectar
cliente_mqtt.on_message = al_recibir

cliente_mqtt.connect(
    BROKER,
    PORT,
    60
)

cliente_mqtt.loop_start()


# -------------------------------------------------
# FLASK
# -------------------------------------------------

@app.route("/")
def inicio():

    return render_template(
        "index.html"
    )


@app.route("/api/datos")
def obtener_datos():

    return jsonify(
        datos
    )


# -------------------------------------------------
# OPTIMIZACION DE TRANSPORTE
# -------------------------------------------------

@app.route("/api/optimizacion/transporte", methods=["POST"])
def optimizar_transporte():
    """Calcula una asignacion de compras sin intervenir en el subsistema IoT."""
    contenido = request.get_json(silent=True) or {}
    metodo = str(contenido.get("metodo", "vogel")).strip().lower()

    argumentos = {
        "costs": contenido.get("costos"),
        "supply": contenido.get("oferta"),
        "demand": contenido.get("demanda"),
        "supplier_names": contenido.get("proveedores"),
        "destination_names": contenido.get("destinos")
    }

    try:
        if metodo == "comparar":
            resultados = [
                solve_transport(method=clave, **argumentos)
                for clave in METHOD_NAMES
            ]
            mejor = min(resultados, key=lambda resultado: resultado["costo_total"])

            return jsonify({
                "ok": True,
                "modo": "comparar",
                "resultados": resultados,
                "mejor_metodo": mejor["metodo"],
                "mejor_costo": mejor["costo_total"]
            })

        resultado = solve_transport(method=metodo, **argumentos)
        return jsonify({
            "ok": True,
            "modo": "individual",
            "resultado": resultado
        })

    except TransportValidationError as error:
        return jsonify({"ok": False, "error": str(error)}), 400
    except Exception as error:
        print("[OPTIMIZACION] Error calculando transporte:", error)
        return jsonify({
            "ok": False,
            "error": "No se pudo completar la optimizacion"
        }), 500


# -------------------------------------------------
# PROGRAMACION LINEAL CON SENSORES
# -------------------------------------------------

@app.route("/api/optimizacion/recursos", methods=["POST"])
def optimizar_recursos_del_aula():
    """Genera un plan energetico con las lecturas MQTT mas recientes."""
    contenido = request.get_json(silent=True) or {}

    try:
        resultado = optimize_sensor_resources(
            datos,
            contenido.get("presupuesto", 120)
        )
        return jsonify({"ok": True, "resultado": resultado})

    except LinearOptimizationError as error:
        return jsonify({"ok": False, "error": str(error)}), 400
    except Exception as error:
        print("[OPTIMIZACION] Error en programacion lineal:", error)
        return jsonify({
            "ok": False,
            "error": "No se pudo calcular el plan lineal"
        }), 500


# -------------------------------------------------
# REGISTRO DE ESTUDIANTES
# -------------------------------------------------

@app.route("/api/estudiantes", methods=["GET", "POST"])
def gestionar_estudiantes():

    global mongo_db

    if mongo_db is None and not conectar_mongo():
        return jsonify({
            "ok": False,
            "error": "MongoDB no está conectado"
        }), 503

    if request.method == "GET":
        try:
            estudiantes = list(
                mongo_db["students"]
                .find({}, {"_id": 0})
                .sort("created_at", -1)
                .limit(200)
            )

            return jsonify({
                "ok": True,
                "estudiantes": [
                    {
                        "nombre": estudiante.get("nombre", ""),
                        "carnet": estudiante.get("carnet", ""),
                        "created_at": convertir_timestamp(
                            estudiante.get("created_at")
                        )
                    }
                    for estudiante in estudiantes
                ]
            })

        except Exception as error:
            print("[DB] Error consultando estudiantes:", error)
            mongo_db = None

            return jsonify({
                "ok": False,
                "error": "No se pudo consultar el registro"
            }), 503

    contenido = request.get_json(silent=True) or {}
    nombre = " ".join(str(contenido.get("nombre", "")).split())
    carnet = str(contenido.get("carnet", "")).strip().upper()

    if len(nombre) < 2 or len(nombre) > 100:
        return jsonify({
            "ok": False,
            "error": "El nombre debe tener entre 2 y 100 caracteres"
        }), 400

    if not re.fullmatch(r"[A-Z0-9-]{4,20}", carnet):
        return jsonify({
            "ok": False,
            "error": "El carné debe tener entre 4 y 20 caracteres alfanuméricos"
        }), 400

    estudiante = {
        "nombre": nombre,
        "carnet": carnet,
        "created_at": datetime.now(timezone.utc)
    }

    try:
        mongo_db["students"].insert_one(estudiante)

        return jsonify({
            "ok": True,
            "estudiante": {
                "nombre": nombre,
                "carnet": carnet,
                "created_at": convertir_timestamp(estudiante["created_at"])
            }
        }), 201

    except DuplicateKeyError:
        return jsonify({
            "ok": False,
            "error": "Ya existe un estudiante con ese carné"
        }), 409

    except Exception as error:
        print("[DB] Error registrando estudiante:", error)
        mongo_db = None

        return jsonify({
            "ok": False,
            "error": "No se pudo guardar el estudiante"
        }), 503


# -------------------------------------------------
# HISTORIAL MONGODB
# -------------------------------------------------

@app.route("/api/historial")
def obtener_historial():

    global mongo_db

    # Si Mongo falló al iniciar, intentamos
    # reconectar cuando el dashboard pida historial.
    if mongo_db is None:

        if not conectar_mongo():

            return jsonify({
                "ok": False,
                "error": "MongoDB no está conectado"
            }), 503


    limite = request.args.get(
        "limite",
        default=20,
        type=int
    )

    if limite < 1:
        limite = 1

    if limite > 100:
        limite = 100


    historial = {
        "temperatura": [],
        "humedad": [],
        "gas": [],
        "distancia": [],
        "luz": [],
        "eventos": [],
        "comandos": []
    }


    try:

        # --------------------------------------
        # SENSORES
        # --------------------------------------

        sensores = [
            "temperatura",
            "humedad",
            "gas",
            "distancia",
            "luz"
        ]


        for nombre in sensores:

            registros = list(
                mongo_db["sensor_readings"]
                .find(
                    {"sensor": nombre},
                    {"_id": 0}
                )
                .sort(
                    "timestamp",
                    -1
                )
                .limit(
                    limite
                )
            )

            registros.reverse()


            for registro in registros:

                historial[nombre].append({
                    "value": registro.get(
                        "value"
                    ),

                    "timestamp":
                        convertir_timestamp(
                            registro.get(
                                "timestamp"
                            )
                        )
                })


        # --------------------------------------
        # EVENTOS
        # --------------------------------------

        eventos = list(
            mongo_db["events"]
            .find(
                {},
                {"_id": 0}
            )
            .sort(
                "timestamp",
                -1
            )
            .limit(
                10
            )
        )


        for evento in eventos:

            historial["eventos"].append({
                "tipo": evento.get(
                    "type",
                    ""
                ),

                "descripcion": evento.get(
                    "description",
                    ""
                ),

                "timestamp":
                    convertir_timestamp(
                        evento.get(
                            "timestamp"
                        )
                    )
            })


        # --------------------------------------
        # COMANDOS
        # --------------------------------------

        comandos = list(
            mongo_db["commands"]
            .find(
                {},
                {"_id": 0}
            )
            .sort(
                "timestamp",
                -1
            )
            .limit(
                10
            )
        )


        for comando in comandos:

            historial["comandos"].append({
                "comando": comando.get(
                    "comando",
                    ""
                ),

                "timestamp":
                    convertir_timestamp(
                        comando.get(
                            "timestamp"
                        )
                    )
            })


        return jsonify({
            "ok": True,
            "historial": historial
        })


    except Exception as error:

        print(
            "[DB] Error consultando historial:",
            error
        )

        # Forzamos reconexión en la siguiente petición.
        mongo_db = None

        return jsonify({
            "ok": False,
            "error": "No se pudo consultar el historial"
        }), 503


# -------------------------------------------------
# CONTROL REMOTO
# -------------------------------------------------

@app.route("/api/control", 
        methods=["POST"])

def control_remoto():
    comando = request.get_json(silent=True)

    if not comando:
        return jsonify({"ok": False, "error": "Comando inválido"}), 400

    dispositivo = comando.get("dispositivo")
    accion = comando.get("accion")

    if not dispositivo or not accion:
        return jsonify({"ok": False, "error": "Falta dispositivo o acción"}), 400

    # Mapear acciones a comandos que entiende main.py
    if dispositivo == "puerta":
        if accion == "ABRIR":
            mensaje = "ABRIR_PUERTA"
        elif accion == "CERRAR":
            mensaje = "CERRAR_PUERTA"
        elif accion == "TOGGLE":
            mensaje = "TOGGLE_PUERTA"
        else:
            mensaje = f"{dispositivo}_{accion}".upper()

    elif dispositivo == "luces":
        if accion == "ENCENDER":
            mensaje = "ENCENDER_LUCES"
        elif accion == "APAGAR":
            mensaje = "APAGAR_LUCES"
        elif accion == "TOGGLE":
            mensaje = "TOGGLE_LUCES"
        elif accion == "AUTOMATICO":
            mensaje = "MODO_AUTO"
        elif accion == "MANUAL":
            mensaje = "MODO_MANUAL"
        else:
            mensaje = f"{dispositivo}_{accion}".upper()

    elif dispositivo == "ventilador":
        if accion == "ENCENDER":
            mensaje = "TOGGLE_VENTILADOR"
        elif accion == "APAGAR":
            mensaje = "TOGGLE_VENTILADOR"
        else:
            mensaje = "TOGGLE_VENTILADOR"

    elif dispositivo == "alarma":
        if accion == "SILENCIAR":
            mensaje = "SILENCIAR_ALARMA"
        else:
            mensaje = "SILENCIAR_ALARMA"

    elif dispositivo == "sistema":
        if accion == "RESTABLECER":
            mensaje = "RESTABLECER_ALERTA"
        else:
            mensaje = "RESTABLECER_ALERTA"

    else:
        mensaje = f"{dispositivo}_{accion}".upper()

    topic = f"{BASE}/control/remoto"
    resultado = cliente_mqtt.publish(topic, mensaje)

    print(f"[CONTROL] Comando remoto: {mensaje}")

    return jsonify({
        "ok": True,
        "mensaje": mensaje,
        "mqtt_rc": resultado.rc
    })


# -------------------------------------------------
# INICIAR SERVIDOR
# -------------------------------------------------

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
        use_reloader=False
    )
