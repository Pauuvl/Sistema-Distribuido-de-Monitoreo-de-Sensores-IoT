from http.server import BaseHTTPRequestHandler, HTTPServer
import json

HOST = "localhost"
PORT = 5000

# Usuarios simulados
USERS = {
    "admin": {"password": "1234", "role": "operator"},
    "user": {"password": "abcd", "role": "viewer"}
}

class AuthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path.startswith("/auth"):
            try:
                query = self.path.split("?")[1]
                params = dict(q.split("=") for q in query.split("&"))

                username = params.get("user")
                password = params.get("pass")

                if username in USERS and USERS[username]["password"] == password:
                    response = {
                        "status": "OK",
                        "role": USERS[username]["role"]
                    }
                    self.send_response(200)
                else:
                    response = {"status": "FAIL"}
                    self.send_response(401)

            except:
                response = {"status": "ERROR"}
                self.send_response(400)

            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

def run():
    server = HTTPServer((HOST, PORT), AuthHandler)
    print(f"Auth Service running on {HOST}:{PORT}")
    server.serve_forever()

if __name__ == "__main__":
    run()