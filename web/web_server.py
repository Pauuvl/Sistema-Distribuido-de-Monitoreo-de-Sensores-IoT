import socket
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse
import requests

# ==============================
# CONFIGURACIÓN
# ==============================

HOST = "0.0.0.0"
PORT = 9090

IOT_SERVER_HOST = "iot-monitoring.com"  # dominio (NO IP)
IOT_SERVER_PORT = 9090

AUTH_SERVICE_URL = "http://localhost:5000/auth"


# ==============================
# FUNCIONES AUXILIARES
# ==============================

def get_sensors_from_iot():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((IOT_SERVER_HOST, IOT_SERVER_PORT))

        s.send("REGISTER OPERATOR web\n".encode())
        s.send("GET SENSORS\n".encode())

        data = s.recv(1024).decode()
        s.close()

        return data

    except Exception as e:
        return f"Error conectando a IoT: {e}"


# ==============================
# SERVIDOR HTTP
# ==============================

class MyHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        # ===== LOGIN PAGE =====
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()

            html = """
            <html>
            <body>
                <h1>Login IoT</h1>
                <form method="POST" action="/login">
                    Usuario: <input type="text" name="user">
                    <input type="submit" value="Ingresar">
                </form>
            </body>
            </html>
            """

            self.wfile.write(html.encode())


        # ===== STATUS PAGE =====
        elif self.path == "/status":

            data = get_sensors_from_iot()

            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()

            html = f"""
            <html>
            <body>
                <h1>Estado del Sistema</h1>
                <pre>{data}</pre>
                <br>
                <a href="/status">Actualizar</a>
            </body>
            </html>
            """

            self.wfile.write(html.encode())

        else:
            self.send_response(404)
            self.end_headers()


    def do_POST(self):

        # ===== LOGIN =====
        if self.path == "/login":

            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length).decode()

            params = urllib.parse.parse_qs(body)
            user = params.get("user", [""])[0]

            try:
                r = requests.post(AUTH_SERVICE_URL, data={"user": user})

                if r.status_code == 200:
                    # REDIRECCIÓN A STATUS
                    self.send_response(302)
                    self.send_header('Location', '/status')
                    self.end_headers()
                else:
                    self.send_response(401)
                    self.end_headers()
                    self.wfile.write(b"Login fallido")

            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"Error auth: {e}".encode())


# ==============================
# MAIN
# ==============================

if __name__ == "__main__":
    server = HTTPServer((HOST, PORT), MyHandler)
    print(f"Web server running on port {PORT}")
    server.serve_forever()