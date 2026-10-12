import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from pymongo import MongoClient

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from iot import globals as gl

class MongoDBManager:
    def __init__(self):
        """Inicializa la conexión y define las colecciones del sistema."""
        load_dotenv()
        uri = os.getenv("MONGO_URI")
        
        try:
            self.client = MongoClient(uri)
            self.db = self.client["edificio_iot"]
            
            # Colecciones obligatorias según el enunciado
            self.col_sensor_readings = self.db["sensor_readings"]
            self.col_events = self.db["events"]
            self.col_commands = self.db["commands"]
            self.col_system_status = self.db["system_status"]
            self.col_students = self.db["students"]
            self.col_students.create_index("carnet", unique=True)
            print("[DB] Conexión a MongoDB Atlas establecida correctamente.")
        except Exception as e:
            print(f"[DB] Error de conexión a la base de datos: {e}")

    def get_timestamp(self):
        """Genera el ISODate nativo requerido para las gráficas."""
        return datetime.now(timezone.utc)

    def insert_sensor_reading(self, sensor_name, value):
        """Almacena las lecturas de los sensores."""
        document = {
            "sensor": sensor_name,
            "value": value,
            "timestamp": self.get_timestamp()
        }
        self.col_sensor_readings.insert_one(document)

    def insert_event(self, event_type, description):
        """Registra alertas, emergencias y eventos de actuadores."""
        document = {
            "type": event_type,
            "description": description,
            "timestamp": self.get_timestamp()
        }
        self.col_events.insert_one(document)

    def update_system_status(self, status):
        """Registra el cambio de estado global del edificio."""
        document = {
            "status": status,
            "timestamp": self.get_timestamp()
        }
        self.col_system_status.insert_one(document)

# Bloque de comprobación aislado
if __name__ == "__main__":
    db_manager = MongoDBManager()
    db_manager.update_system_status("NORMAL")
    print("Prueba completada: Verifica en Atlas la colección 'system_status'.")
