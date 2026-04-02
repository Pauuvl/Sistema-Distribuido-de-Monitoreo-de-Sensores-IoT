from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse

class AuthHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        if self.path == "/auth":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode()

            params = urllib.parse.parse_qs(post_data)
            user = params.get("user", [""])[0]

            if user == "admin":
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"OK")
            else:
                self.send_response(401)
                self.end_headers()
                self.wfile.write(b"FAIL")

        else:
            self.send_response(404)
            self.end_headers()

def run():
    server = HTTPServer(('localhost', 5000), AuthHandler)
    print("Auth Service running on localhost:5000")
    server.serve_forever()

if __name__ == "__main__":
    run()