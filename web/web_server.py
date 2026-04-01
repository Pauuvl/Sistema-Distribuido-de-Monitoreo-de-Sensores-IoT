from http.server import BaseHTTPRequestHandler, HTTPServer
import socket
import json

HOST = "localhost"
PORT = 8000

IOT_SERVER_HOST = "localhost"
IOT_SERVER_PORT = 8080

AUTH_HOST = "localhost"
AUTH_PORT = 5000

class WebHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        # ================= LOGIN =================
        if self.path.startswith("/login"):
            try:
                query = self.path.split("?")[1]
                params = dict(q.split("=") for q in query.split("&"))

                user = params.get("user")
                password = params.get("pass")

                # llamar auth service
                auth_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                auth_socket.connect((AUTH_HOST, AUTH_PORT))

                request = f"GET /auth?user={user}&pass={password} HTTP/1.1\r\nHost: localhost\r\n\r\n"
                auth_socket.send(request.encode())

                response = auth_socket.recv(1024).decode()
                auth_socket.close()

                if "200 OK" in response:
                    self.send_response(200)
                    self.end_headers()
                    self.send_response(302)
                    self.send_header("Location", "/status")
                    self.end_headers()
                else:
                    self.send_response(401)
                    self.end_headers()
                    self.wfile.write(b"Login fallido")

            except:
                self.send_response(400)
                self.end_headers()

        # ================= ESTADO =================
        elif self.path == "/status":
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect((IOT_SERVER_HOST, IOT_SERVER_PORT))

                s.send(b"GET SENSORS\n")
                data = s.recv(1024).decode()

                s.close()

                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()

                html = f"""
                <html>
                <body>
                <h1>Estado del Sistema IoT</h1>

                <h2>Sensores Activos</h2>
                <pre>{data}</pre>

                <h2>Opciones</h2>
                <a href="/">Volver</a>

                </body>
                </html>
                """
                self.wfile.write(html.encode())

            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())

        # ================= HOME =================
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()

            html = """
            <html>
            <body>
                <h1>IoT Monitoring</h1>

                <h2>Login</h2>
                <form action="/login">
                    Usuario: <input name="user"><br>
                    Password: <input name="pass"><br>
                    <input type="submit" value="Login">
                </form>

                <h2>Opciones</h2>
                <a href="/status">Ver estado del sistema</a>
            </body>
            </html>
            """

            self.wfile.write(html.encode())

def run():
    server = HTTPServer((HOST, PORT), WebHandler)
    print(f"Web server running on http://{HOST}:{PORT}")
    server.serve_forever()

if __name__ == "__main__":
    run()