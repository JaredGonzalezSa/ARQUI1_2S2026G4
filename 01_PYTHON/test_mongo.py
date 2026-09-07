import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.server_api import ServerApi  # <--- IMPORTAR ServerApi

# Cargar la URI desde el archivo .env
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

def probar_conexion():
    try:
        print("Conectando a MongoDB Atlas...")
        
        # Usar ServerApi para compatibilidad con MongoDB Atlas
        client = MongoClient(
            MONGO_URI,
            server_api=ServerApi("1")  # <--- CLAVE: ServerApi
        )
        
        # Seleccionar la base de datos y la colección
        db = client["edificio_iot"]
        coleccion = db["sensor_readings"]
        
        # Crear un documento de prueba
        documento_prueba = {
            "temperatura": 30,
            "humedad": 30,
            "gas": 30,
            "distancia": 30,
            "luz": 30,
            "timestamp": datetime.now(timezone.utc) 
        }
        
        # Insertar el documento
        resultado = coleccion.insert_one(documento_prueba)
        print(f"¡Éxito! Documento insertado con el ID: {resultado.inserted_id}")
        print(f"✅ Revisa en Atlas: base de datos 'edificio_iot', colección 'sensor_readings'")
        
    except Exception as e:
        print(f"Error de conexión: {e}")

if __name__ == "__main__":
    probar_conexion()