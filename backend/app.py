import json
import os

from flask import Flask, jsonify, render_template, request
import paho.mqtt.client as mqtt

from datetime import timezone
from dotenv import load_dotenv
from pymongo import MongoClient


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

    "arm64": {
        "max": 0,
        "min": 0,
        "avg": 0,
        "count": 0
    },

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
# RESULTADO ARM64
# -------------------------------------------------

def leer_resultado_arm64(contenido):

    # Formato JSON
    try:

        resultado = json.loads(
            contenido
        )

        return {
            "max": int(
                resultado.get(
                    "max",
                    resultado.get(
                        "maximo",
                        0
                    )
                )
            ),

            "min": int(
                resultado.get(
                    "min",
                    resultado.get(
                        "minimo",
                        0
                    )
                )
            ),

            "avg": int(
                resultado.get(
                    "avg",
                    resultado.get(
                        "promedio",
                        0
                    )
                )
            ),

            "count": int(
                resultado.get(
                    "count",
                    resultado.get(
                        "cantidad",
                        0
                    )
                )
            )
        }

    except Exception:
        pass


    # Formato del backend:
    # MAX:35,MIN:20,AVG:27,COUNT:20
    try:

        valores = {}

        partes = contenido.split(",")

        for parte in partes:

            clave, valor = parte.split(
                ":",
                1
            )

            valores[
                clave.strip().upper()
            ] = int(
                valor.strip()
            )

        return {
            "max": valores["MAX"],
            "min": valores["MIN"],
            "avg": valores["AVG"],
            "count": valores["COUNT"]
        }

    except Exception as error:

        print(
            "[ARM64] No se pudo interpretar "
            "el resultado:",
            error
        )

        return None


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


def al_recibir(
    client,
    userdata,
    mensaje
):

    topic = mensaje.topic
    contenido = mensaje.payload.decode("utf-8")

    print(topic, "->", contenido)

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
        # Soporta tanto JSON como texto plano
        try:
            estado_luces = json.loads(contenido)
            datos["modo_iluminacion"] = estado_luces.get("modo", datos["modo_iluminacion"])
            datos["zona1"] = estado_luces.get("zona1", datos["zona1"])
            datos["zona2"] = estado_luces.get("zona2", datos["zona2"])
            datos["zona3"] = estado_luces.get("zona3", datos["zona3"])
            datos["luces"] = f"Z1:{datos['zona1']} Z2:{datos['zona2']} Z3:{datos['zona3']}"
        except json.JSONDecodeError:
            # Texto plano: "ON", "OFF", "AUTO_ON", "AUTO_OFF", "MODO_AUTO", "MODO_MANUAL"
            if contenido in ("ON", "AUTO_ON"):
                datos["luces"] = "ENCENDIDAS"
                datos["zona1"] = "ENCENDIDA"
                datos["zona2"] = "ENCENDIDA"
                datos["zona3"] = "ENCENDIDA"
                # Si llega AUTO_ON, el modo es automático
                if contenido == "AUTO_ON":
                    datos["modo_iluminacion"] = "AUTOMATICO"
            elif contenido in ("OFF", "AUTO_OFF"):
                datos["luces"] = "APAGADAS"
                datos["zona1"] = "APAGADA"
                datos["zona2"] = "APAGADA"
                datos["zona3"] = "APAGADA"
                if contenido == "AUTO_OFF":
                    datos["modo_iluminacion"] = "AUTOMATICO"
            elif contenido == "MODO_AUTO":
                datos["modo_iluminacion"] = "AUTOMATICO"
            elif contenido == "MODO_MANUAL":
                datos["modo_iluminacion"] = "MANUAL"
            else:
                datos["luces"] = contenido

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

    # ------------------------------------------
    # RESULTADOS ARM64
    # ------------------------------------------

    elif topic == f"{BASE}/arm64/resultados":
        resultado = leer_resultado_arm64(contenido)
        if resultado:
            datos["arm64"] = resultado


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
        "arm64": [],
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
        # ARM64
        # --------------------------------------

        resultados_arm64 = list(
            mongo_db["arm64_results"]
            .find(
                {},
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

        resultados_arm64.reverse()


        for resultado in resultados_arm64:

            historial["arm64"].append({
                "max": resultado.get(
                    "maximo"
                ),

                "min": resultado.get(
                    "minimo"
                ),

                "avg": resultado.get(
                    "promedio"
                ),

                "count": resultado.get(
                    "cantidad"
                ),

                "timestamp":
                    convertir_timestamp(
                        resultado.get(
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
