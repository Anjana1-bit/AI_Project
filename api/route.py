from http.server import BaseHTTPRequestHandler
import json

from src.serverless_service import city_for, route_data


class handler(BaseHTTPRequestHandler):
    def log_message(self, _format, *_args):
        pass

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            request = json.loads(self.rfile.read(length) or b"{}")
            start, destination = request.get("start"), request.get("destination")
            algorithm = request.get("algorithm", "astar")
            updated = bool(request.get("updated", False))
            if start not in city_for(updated).graph or destination not in city_for(updated).graph or start == destination:
                raise ValueError("Choose two different valid locations.")
            data, status = route_data(start, destination, algorithm, updated), 200
        except (ValueError, KeyError, json.JSONDecodeError) as error:
            data, status = {"error": str(error) if str(error) else "Invalid route request."}, 400
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
