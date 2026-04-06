from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse

# Usuarios del sistema con sus roles
USERS = {
    "admin":     "operator",
    "helen":     "operator",
    "paulina":   "operator",
    "sensor1":   "sensor",
    "sensor2":   "sensor",
}


class AuthHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        if self.path == "/auth":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode()

            params = urllib.parse.parse_qs(post_data)
            user = params.get("user", [""])[0]

            if user in USERS:
                role = USERS[user]
                self.send_response(200)
                self.end_headers()
                self.wfile.write(f"OK role={role}".encode())
            else:
                self.send_response(401)
                self.end_headers()
                self.wfile.write(b"FAIL")

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Silenciar logs de HTTP por defecto para que no ensucien la consola
        pass


def run():
    server = HTTPServer(('localhost', 5000), AuthHandler)
    print("Auth Service corriendo en localhost:5000")
    server.serve_forever()


if __name__ == "__main__":
    run()