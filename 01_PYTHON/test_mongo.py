import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from pymongo import MongoClient

class MongoDBManager:
    def __init__(self):
        """Inicializa la conexión y define las 5 colecciones obligatorias."""
        load_dotenv()
        uri = os.getenv("MONGO_URI")
        
        if not uri:
            print("[DB] ERROR: MONGO_URI no encontrada en .env")
            return
        
        try:
            # SOLUCIÓN: Ignorar verificación SSL
            self.client = MongoClient(
                uri,
                tlsAllowInvalidCertificates=True,  # <--- CLAVE
                tlsAllowInvalidHostnames=True,      # <--- CLAVE
                serverSelectionTimeoutMS=5000       # Timeout más corto
            )
            
            # Forzar una pequeña operación para verificar conexión
            self.client.admin.command('ping')
            
            self.db = self.client["edificio_iot"]
            
            self.col_sensor_readings = self.db["sensor_readings"]
            self.col_events = self.db["events"]
            self.col_commands = self.db["commands"]
            self.col_arm64_results = self.db["arm64_results"]
            self.col_system_status = self.db["system_status"]
            print("[DB] Conexión a MongoDB Atlas establecida correctamente.")
            
        except Exception as e:
            print(f"[DB] Error de conexión a la base de datos: {e}")
            # Si falla, mostrar más detalles
            import traceback
            traceback.print_exc()

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

    def insert_arm64_result(self, max_val, min_val, avg_val, count_val):
        """Registra los cálculos devueltos por el módulo en ensamblador."""
        document = {
            "maximo": max_val,
            "minimo": min_val,
            "promedio": avg_val,
            "cantidad": count_val,
            "timestamp": self.get_timestamp()
        }
        self.col_arm64_results.insert_one(document)
        print("[DB] Resultados de ARM64 guardados en Atlas.")

# Bloque de comprobación aislado
if __name__ == "__main__":
    db_manager = MongoDBManager()
    db_manager.update_system_status("NORMAL")
    print("Prueba completada: Verifica en Atlas la colección 'system_status'.")