"""Local web interface for the AI Emergency Traffic Routing System.

Run: .venv/bin/python web_app.py
Open: http://127.0.0.1:8000
"""

from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from app import EmergencyRoadNetwork, apply_dynamic_event, build_demo_city

PROJECT_DIR = Path(__file__).resolve().parent
city: EmergencyRoadNetwork = build_demo_city()
updated = False


def route_data(start: str, destination: str, algorithm: str) -> dict:
    choices = {
        "astar": ("A* (Utility-Aware)", city.astar),
        "bfs": ("BFS (Fewest Roads)", city.bfs),
        "greedy": ("Greedy Best-First", city.greedy_best_first),
    }
    name, search = choices[algorithm]
    result = city.run_algorithm(name, search, start, destination)
    return {
        "algorithm": result.algorithm,
        "path": result.path,
        "distance": None if result.path is None else round(result.distance_km, 1),
        "minutes": None if result.path is None else round(result.travel_minutes, 1),
        "utility": None if result.path is None else round(result.utility_cost, 2),
    }


def network_data() -> dict:
    return {
        "nodes": [{"name": name, "x": data["pos"][0], "y": data["pos"][1]} for name, data in city.graph.nodes(data=True)],
        "edges": [
            {"from": a, "to": b, "distance": data["distance"], "traffic": data["traffic"], "blocked": data["blocked"]}
            for a, b, data in city.graph.edges(data=True)
        ],
        "updated": updated,
    }


class RoutingHandler(BaseHTTPRequestHandler):
    def log_message(self, _format: str, *_args: object) -> None:
        """Keep browser requests out of the classroom console."""

    def send_json(self, data: dict, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/network":
            self.send_json(network_data())
            return
        if path in ("/", "/index.html"):
            page = (PROJECT_DIR / "index.html").read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(page)))
            self.end_headers()
            self.wfile.write(page)
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        global city, updated
        length = int(self.headers.get("Content-Length", "0"))
        try:
            request = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self.send_json({"error": "Request must contain valid JSON."}, HTTPStatus.BAD_REQUEST)
            return
        path = urlparse(self.path).path
        if path == "/api/route":
            start, destination = request.get("start"), request.get("destination")
            if start not in city.graph or destination not in city.graph or start == destination:
                self.send_json({"error": "Choose two different valid locations."}, HTTPStatus.BAD_REQUEST)
                return
            try:
                self.send_json(route_data(start, destination, request.get("algorithm", "astar")))
            except KeyError:
                self.send_json({"error": "Unknown algorithm."}, HTTPStatus.BAD_REQUEST)
            return
        if path == "/api/update":
            if not updated:
                apply_dynamic_event(city)
                updated = True
            self.send_json(network_data())
            return
        if path == "/api/reset":
            city = build_demo_city()
            updated = False
            self.send_json(network_data())
            return
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
