import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from pymongo import MongoClient

# Cargar la URI desde el archivo .env
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

def probar_conexion():
    try:
        print("Conectando a MongoDB Atlas...")
        client = MongoClient(MONGO_URI)
        
        # Seleccionar la base de datos y la colección
        db = client["edificio_iot"]
        coleccion = db["sensor_readings"]
        
        # Crear un documento de prueba (Mockup)
        # Usamos datetime.now(timezone.utc) para que Atlas lo guarde como ISODate nativo
        documento_prueba = {
            "temperatura": 24,
            "humedad": 55,
            "gas": 300,
            "distancia": 15,
            "luz": 800,
            "timestamp": datetime.now(timezone.utc) 
        }
        
        # Insertar el documento
        resultado = coleccion.insert_one(documento_prueba)
        print(f"¡Éxito! Base de datos conectada y documento insertado con el ID: {resultado.inserted_id}")
        
    except Exception as e:
        print(f"Error de conexión: {e}")

if __name__ == "__main__":
    probar_conexion()