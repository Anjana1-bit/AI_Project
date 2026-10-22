"""Run the local browser interface with: python -m src.local_server."""

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from src.serverless_service import city_for, network_data, route_data

PROJECT_DIR = Path(__file__).resolve().parent.parent


class RoutingHandler(BaseHTTPRequestHandler):
    def log_message(self, _format, *_args):
        pass

    def send_json(self, data, status=HTTPStatus.OK):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/network":
            self.send_json(network_data())
        elif path in ("/", "/index.html"):
            page = (PROJECT_DIR / "index.html").read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(page)))
            self.end_headers()
            self.wfile.write(page)
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            request = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self.send_json({"error": "Request must contain valid JSON."}, HTTPStatus.BAD_REQUEST)
            return
        path = urlparse(self.path).path
        blocked_roads = request.get("blocked_roads", [])
        if path == "/api/route":
            start, destination = request.get("start"), request.get("destination")
            if start not in city_for(blocked_roads).graph or destination not in city_for(blocked_roads).graph or start == destination:
                self.send_json({"error": "Choose two different valid locations."}, HTTPStatus.BAD_REQUEST)
                return
            try:
                self.send_json(route_data(start, destination, request.get("algorithm", "astar"), blocked_roads))
            except KeyError:
                self.send_json({"error": "Unknown algorithm."}, HTTPStatus.BAD_REQUEST)
        elif path == "/api/update":
            self.send_json(network_data(blocked_roads))
        elif path == "/api/reset":
            self.send_json(network_data())
        else:
            self.send_error(HTTPStatus.NOT_FOUND)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8000), RoutingHandler)
    print("Emergency Routing web app running at http://127.0.0.1:8000")
    print("Press Ctrl+C to stop the server.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()
