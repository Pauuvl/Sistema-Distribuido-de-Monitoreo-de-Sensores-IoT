import socket
import time
import random
import threading
from datetime import datetime

# CONFIGURACIÓN — NO usar IP fija (requisito)
# Cuando Juan configure el DNS, cambia esto
# por el dominio, ej: "iot.midominio.com"

SERVER_HOST = "localhost"   # <-- cambiar por dominio DNS al desplegar
SERVER_PORT = 9090
SEND_INTERVAL = 5           # segundos entre mediciones
PING_INTERVAL = 20          # segundos entre PINGs
RECONNECT_WAIT = 5          # segundos antes de reintentar conexión

# DEFINICIÓN DE LOS 5 SENSORES
SENSORS = [
    {"id": "sensor-001", "tipo": "temp"},
    {"id": "sensor-002", "tipo": "temp"},
    {"id": "sensor-003", "tipo": "vibr"},
    {"id": "sensor-004", "tipo": "vibr"},
    {"id": "sensor-005", "tipo": "energy"},
]

# GENERADOR DE VALORES SIMULADOS
def generate_value(tipo):
    """Genera un valor simulado realista según el tipo de sensor."""
    if tipo == "temp":
        # Mayoría normal, ocasionalmente anómalo
        base = random.uniform(20.0, 40.0)
        if random.random() < 0.15:   # 15% de probabilidad de anomalía
            base = random.uniform(76.0, 100.0)
        return round(base, 2)

    elif tipo == "vibr":
        base = random.uniform(0.5, 2.5)
        if random.random() < 0.1:
            base = random.uniform(3.1, 8.0)
        return round(base, 2)

    elif tipo == "energy":
        base = random.uniform(100.0, 350.0)
        if random.random() < 0.1:
            base = random.uniform(401.0, 650.0)
        return round(base, 2)

    return 0.0


class Sensor:
    def __init__(self, sensor_id, tipo):
        self.sensor_id = sensor_id
        self.tipo = tipo
        self.sock = None
        self.connected = False
        self.running = True

    def connect(self):
        """Intenta conectarse al servidor. Reintenta si falla."""
        while self.running:
            try:
                # Resolución de nombres (NO IP fija)
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.settimeout(10)
                self.sock.connect((SERVER_HOST, SERVER_PORT))
                self.connected = True
                print(f"[{self.sensor_id}] Conectado al servidor {SERVER_HOST}:{SERVER_PORT}")
                return True
            except socket.gaierror as e:
                # Error de resolución DNS
                print(f"[{self.sensor_id}] Error DNS al resolver '{SERVER_HOST}': {e}")
                print(f"[{self.sensor_id}] Reintentando en {RECONNECT_WAIT}s...")
                time.sleep(RECONNECT_WAIT)
            except (socket.timeout, ConnectionRefusedError, OSError) as e:
                # Error de red
                print(f"[{self.sensor_id}] Error de conexión: {e}")
                print(f"[{self.sensor_id}] Reintentando en {RECONNECT_WAIT}s...")
                time.sleep(RECONNECT_WAIT)
        return False

    def send_message(self, msg):
        """Envía un mensaje al servidor. Devuelve False si falla."""
        try:
            self.sock.sendall((msg + "\n").encode("utf-8"))
            return True
        except (BrokenPipeError, OSError) as e:
            print(f"[{self.sensor_id}] Error al enviar: {e}")
            self.connected = False
            return False

    def receive_response(self):
        """Lee una línea de respuesta del servidor."""
        try:
            self.sock.settimeout(5)
            response = b""
            while True:
                chunk = self.sock.recv(1)
                if not chunk or chunk == b"\n":
                    break
                response += chunk
            return response.decode("utf-8").strip()
        except (socket.timeout, OSError):
            return None

    def register(self):
        """Envía REGISTER al servidor."""
        msg = f"REGISTER SENSOR {self.tipo} {self.sensor_id}"
        if not self.send_message(msg):
            return False
        response = self.receive_response()
        if response and response.startswith("OK REGISTERED"):
            print(f"[{self.sensor_id}] Registrado correctamente")
            return True
        else:
            print(f"[{self.sensor_id}] Fallo al registrar: {response}")
            return False

    def send_data(self):
        """Genera y envía una medición al servidor."""
        valor = generate_value(self.tipo)
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        msg = f"DATA {self.sensor_id} {self.tipo} {valor} {timestamp}"
        if not self.send_message(msg):
            return False
        response = self.receive_response()
        if response:
            print(f"[{self.sensor_id}] Enviado {self.tipo}={valor} → {response}")
        return True

    def send_ping(self):
        """Envía PING para mantener conexión activa."""
        if not self.send_message("PING"):
            return False
        response = self.receive_response()
        if response == "PONG":
            print(f"[{self.sensor_id}] PING → PONG ✓")
        return True

    def disconnect(self):
        """Desconexión limpia."""
        try:
            self.send_message("DISCONNECT")
            self.sock.close()
        except:
            pass
        self.connected = False
        print(f"[{self.sensor_id}] Desconectado")

    def run(self):
        """Ciclo de vida completo del sensor con manejo de errores."""
        ping_counter = 0

        while self.running:
            # Intentar conectar (reintenta automáticamente si falla)
            if not self.connect():
                break

            # Registrarse
            if not self.register():
                self.connected = False
                time.sleep(RECONNECT_WAIT)
                continue

            # Ciclo de envío de datos
            while self.running and self.connected:
                # Enviar datos
                if not self.send_data():
                    print(f"[{self.sensor_id}] Conexión perdida. Reconectando...")
                    break

                # Enviar PING cada PING_INTERVAL segundos
                ping_counter += SEND_INTERVAL
                if ping_counter >= PING_INTERVAL:
                    if not self.send_ping():
                        break
                    ping_counter = 0

                time.sleep(SEND_INTERVAL)

            # Si salió del ciclo interno, cerrar socket y reconectar
            try:
                self.sock.close()
            except:
                pass
            self.connected = False

            if self.running:
                print(f"[{self.sensor_id}] Reconectando en {RECONNECT_WAIT}s...")
                time.sleep(RECONNECT_WAIT)

# LANZAR LOS 5 SENSORES EN HILOS SEPARADOS
def main():
    print("=== Sistema de Sensores IoT ===")
    print(f"Servidor: {SERVER_HOST}:{SERVER_PORT}")
    print(f"Sensores configurados: {len(SENSORS)}")
    print("=" * 35)

    threads = []
    sensors = []

    for config in SENSORS:
        sensor = Sensor(config["id"], config["tipo"])
        sensors.append(sensor)
        t = threading.Thread(target=sensor.run, daemon=True)
        threads.append(t)
        t.start()
        time.sleep(0.5)   # pequeño delay entre conexiones

    try:
        # Mantener el programa corriendo
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[SISTEMA] Deteniendo sensores...")
        for sensor in sensors:
            sensor.running = False
        print("[SISTEMA] Sensores detenidos.")

if __name__ == "__main__":
    main()