import socket
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse

IOT_SERVER_HOST = "localhost"
IOT_SERVER_PORT = 8080

AUTH_SERVER_URL = "http://localhost:5000/auth"

class MyHandler(BaseHTTPRequestHandler):

    # =========================
    # GET
    # =========================
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()

            html = """
            <html>
            <body>
                <h2>Login</h2>
                <form method="POST" action="/login">
                    Usuario: <input type="text" name="user"><br><br>
                    <input type="submit" value="Ingresar">
                </form>
            </body>
            </html>
            """

            self.wfile.write(html.encode())

        elif self.path == "/status":
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect((IOT_SERVER_HOST, IOT_SERVER_PORT))

                s.send(b"GET SENSORS\n")
                data = s.recv(1024).decode()

                s.close()

                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()

                html = f"""
                <html>
                <body>
                    <h1>Estado del Sistema IoT</h1>

                    <h2>Sensores Activos</h2>
                    <pre>{data}</pre>

                    <br>
                    <a href="/">Cerrar sesión</a>
                </body>
                </html>
                """

                self.wfile.write(html.encode())

            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())

        else:
            self.send_response(404)
            self.end_headers()

    # =========================
    # POST (LOGIN)
    # =========================
    def do_POST(self):
        if self.path == "/login":
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length).decode()

                params = urllib.parse.parse_qs(post_data)
                user = params.get("user", [""])[0]

                # 🔥 CONEXIÓN AL AUTH SERVER
                res = requests.post(AUTH_SERVER_URL, data={"user": user})

                if res.status_code == 200:
                    self.send_response(302)
                    self.send_header("Location", "/status")
                    self.end_headers()
                else:
                    self.send_response(401)
                    self.end_headers()
                    self.wfile.write(b"Login incorrecto")

            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())

# =========================
# RUN SERVER
# =========================
def run():
    server = HTTPServer(('localhost', 8000), MyHandler)
    print("Servidor web en http://localhost:8000")
    server.serve_forever()

if __name__ == "__main__":
    run()