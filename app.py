"""AI-Based Emergency Traffic Routing System.

Run with: python app.py
The program uses a small simulated city. Change road states in
``apply_dynamic_event`` to demonstrate live re-routing.
"""

from __future__ import annotations

import heapq
import math
import os
from collections import deque
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional, Tuple

# Keep Matplotlib's cache inside the project when the user's home config directory
# is unavailable (for example, in a lab or sandboxed environment).
os.environ.setdefault("MPLCONFIGDIR", os.path.join(os.path.dirname(__file__), ".matplotlib"))

import matplotlib.pyplot as plt
import networkx as nx


TRAFFIC_MULTIPLIER = {"low": 1.0, "medium": 1.45, "high": 2.20}
BASE_SPEED_KMH = 45.0


@dataclass(frozen=True)
class RouteResult:
    """A route found by one search algorithm."""

    algorithm: str
    path: Optional[List[str]]
    utility_cost: float = math.inf
    distance_km: float = math.inf
    travel_minutes: float = math.inf


class EmergencyRoadNetwork:
    """Road graph and search methods used by the ambulance agent."""

    def __init__(self) -> None:
        self.graph = nx.Graph()

    def add_location(self, name: str, x: float, y: float) -> None:
        self.graph.add_node(name, pos=(x, y))

    def add_road(
        self, start: str, end: str, distance: float, traffic: str, risk: float = 0.0
    ) -> None:
        if traffic not in TRAFFIC_MULTIPLIER:
            raise ValueError(f"Unknown traffic level: {traffic}")
        self.graph.add_edge(
            start,
            end,
            distance=distance,
            traffic=traffic,
            risk=risk,
            blocked=False,
        )

    def update_road(
        self, start: str, end: str, *, traffic: Optional[str] = None, blocked: Optional[bool] = None
    ) -> None:
        """Apply an incoming road-status update."""
        if not self.graph.has_edge(start, end):
            raise ValueError(f"No road exists between {start} and {end}")
        if traffic is not None:
            if traffic not in TRAFFIC_MULTIPLIER:
                raise ValueError(f"Unknown traffic level: {traffic}")
            self.graph[start][end]["traffic"] = traffic
        if blocked is not None:
            self.graph[start][end]["blocked"] = blocked

    def edge_cost(self, start: str, end: str) -> float:
        road = self.graph[start][end]
        if road["blocked"]:
            return math.inf
        return road["distance"] * TRAFFIC_MULTIPLIER[road["traffic"]] + road["risk"]

    def heuristic(self, node: str, goal: str) -> float:
        """Euclidean lower bound on remaining cost for A*."""
        x1, y1 = self.graph.nodes[node]["pos"]
        x2, y2 = self.graph.nodes[goal]["pos"]
        return math.hypot(x2 - x1, y2 - y1)

    def open_neighbors(self, node: str) -> Iterable[str]:
        return (neighbor for neighbor in self.graph.neighbors(node) if not self.graph[node][neighbor]["blocked"])

    @staticmethod
    def _reconstruct(came_from: Dict[str, str], current: str) -> List[str]:
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        return list(reversed(path))

    def astar(self, start: str, goal: str) -> Optional[List[str]]:
        frontier: List[Tuple[float, int, str]] = [(self.heuristic(start, goal), 0, start)]
        came_from: Dict[str, str] = {}
        best_cost = {start: 0.0}
        count = 0

        while frontier:
            _, _, current = heapq.heappop(frontier)
            if current == goal:
                return self._reconstruct(came_from, current)
            for neighbor in self.open_neighbors(current):
                candidate = best_cost[current] + self.edge_cost(current, neighbor)
                if candidate < best_cost.get(neighbor, math.inf):
                    came_from[neighbor] = current
                    best_cost[neighbor] = candidate
                    count += 1
                    priority = candidate + self.heuristic(neighbor, goal)
                    heapq.heappush(frontier, (priority, count, neighbor))
        return None

    def bfs(self, start: str, goal: str) -> Optional[List[str]]:
        """Breadth-first search: minimizes number of road segments, not traffic cost."""
        queue = deque([start])
        came_from: Dict[str, str] = {}
        visited = {start}
        while queue:
            current = queue.popleft()
            if current == goal:
                return self._reconstruct(came_from, current)
            for neighbor in self.open_neighbors(current):
                if neighbor not in visited:
                    visited.add(neighbor)
                    came_from[neighbor] = current
                    queue.append(neighbor)
        return None

    def greedy_best_first(self, start: str, goal: str) -> Optional[List[str]]:
        """Greedy best-first search: expands the location appearing closest to the goal."""
        frontier: List[Tuple[float, int, str]] = [(self.heuristic(start, goal), 0, start)]
        came_from: Dict[str, str] = {}
        visited = set()
        count = 0
        while frontier:
            _, _, current = heapq.heappop(frontier)
            if current in visited:
                continue
            visited.add(current)
            if current == goal:
                return self._reconstruct(came_from, current)
            for neighbor in self.open_neighbors(current):
                if neighbor not in visited:
                    if neighbor not in came_from:
                        came_from[neighbor] = current
                    count += 1
                    heapq.heappush(frontier, (self.heuristic(neighbor, goal), count, neighbor))
        return None

    def metrics(self, path: Optional[List[str]]) -> Tuple[float, float, float]:
        if not path:
            return math.inf, math.inf, math.inf
        distance = sum(self.graph[a][b]["distance"] for a, b in zip(path, path[1:]))
        cost = sum(self.edge_cost(a, b) for a, b in zip(path, path[1:]))
        minutes = sum(
            (self.graph[a][b]["distance"] / BASE_SPEED_KMH)
            * 60
            * TRAFFIC_MULTIPLIER[self.graph[a][b]["traffic"]]
            for a, b in zip(path, path[1:])
        )
        return cost, distance, minutes

    def run_algorithm(self, name: str, search: Callable[[str, str], Optional[List[str]]], start: str, goal: str) -> RouteResult:
        path = search(start, goal)
        cost, distance, minutes = self.metrics(path)
        return RouteResult(name, path, cost, distance, minutes)

    def visualize(self, route: Optional[List[str]], title: str, filename: str) -> None:
        """Save a city-map image; red roads are blocked, blue edges form the chosen route."""
        pos = nx.get_node_attributes(self.graph, "pos")
        plt.figure(figsize=(10, 6))
        open_edges = [(a, b) for a, b, data in self.graph.edges(data=True) if not data["blocked"]]
        blocked_edges = [(a, b) for a, b, data in self.graph.edges(data=True) if data["blocked"]]
        nx.draw_networkx_nodes(self.graph, pos, node_color="#d9f0ff", node_size=1700, edgecolors="#1d4e89")
        nx.draw_networkx_labels(self.graph, pos, font_size=9, font_weight="bold")
        nx.draw_networkx_edges(self.graph, pos, edgelist=open_edges, edge_color="#8a8a8a", width=2)
        nx.draw_networkx_edges(self.graph, pos, edgelist=blocked_edges, edge_color="#d62828", width=3, style="dashed")
        if route:
            nx.draw_networkx_edges(self.graph, pos, edgelist=list(zip(route, route[1:])), edge_color="#0066cc", width=5)
        labels = {
            (a, b): f'{data["distance"]} km | {data["traffic"]}' + (" | BLOCKED" if data["blocked"] else "")
            for a, b, data in self.graph.edges(data=True)
        }
        nx.draw_networkx_edge_labels(self.graph, pos, edge_labels=labels, font_size=7)
        plt.title(title, fontweight="bold")
        plt.axis("off")
        plt.tight_layout()
        os.makedirs("outputs", exist_ok=True)
        plt.savefig(os.path.join("outputs", filename), dpi=180, bbox_inches="tight")
        plt.close()


def build_demo_city() -> EmergencyRoadNetwork:
    city = EmergencyRoadNetwork()
    for name, x, y in [
        ("Hospital", 0, 2), ("North Junction", 2, 4), ("Central Square", 3, 2),
        ("West Avenue", 1, 0), ("East Market", 5, 3), ("South Bridge", 4, 0),
        ("Accident Site", 7, 2),
    ]:
        city.add_location(name, x, y)
    city.add_road("Hospital", "North Junction", 2.2, "low", 0.1)
    city.add_road("Hospital", "Central Square", 3.0, "medium", 0.2)
    city.add_road("Hospital", "West Avenue", 2.4, "low", 0.1)
    city.add_road("North Junction", "Central Square", 2.0, "low", 0.1)
    city.add_road("North Junction", "East Market", 3.4, "medium", 0.3)
    city.add_road("Central Square", "East Market", 2.5, "high", 0.3)
    city.add_road("Central Square", "South Bridge", 2.6, "medium", 0.2)
    city.add_road("West Avenue", "South Bridge", 3.2, "low", 0.2)
    city.add_road("East Market", "Accident Site", 2.3, "low", 0.1)
    city.add_road("South Bridge", "Accident Site", 3.5, "low", 0.2)
    return city


def print_results(results: List[RouteResult]) -> None:
    print(f"{'Algorithm':<25} {'Route':<66} {'Distance':>9} {'Time':>10} {'Utility':>10}")
    print("-" * 130)
    for result in results:
        route = " -> ".join(result.path) if result.path else "No safe route"
        print(f"{result.algorithm:<25} {route:<66} {result.distance_km:>7.1f} km {result.travel_minutes:>7.1f} min {result.utility_cost:>10.2f}")


def apply_dynamic_event(city: EmergencyRoadNetwork) -> None:
    """Simulate live traffic data received after the ambulance has started."""
    city.update_road("North Junction", "East Market", traffic="high")
    city.update_road("Central Square", "East Market", blocked=True)


def main() -> None:
    city = build_demo_city()
    start, destination = "Hospital", "Accident Site"

    print("\nAI-BASED EMERGENCY TRAFFIC ROUTING SYSTEM")
    print(f"Mission: ambulance from {start} to {destination}\n")
    initial = [
        city.run_algorithm("A* (utility-aware)", city.astar, start, destination),
        city.run_algorithm("BFS (fewest roads)", city.bfs, start, destination),
        city.run_algorithm("Greedy Best-First", city.greedy_best_first, start, destination),
    ]
    print_results(initial)
    city.visualize(initial[0].path, "Initial A* ambulance route", "initial_route.png")

    print("\nLIVE UPDATE: North Junction -> East Market now has heavy traffic; Central Square -> East Market is blocked.")
    apply_dynamic_event(city)
    current_location = "North Junction"
    reroute = city.run_algorithm("A* re-route", city.astar, current_location, destination)
    print(f"Ambulance current location: {current_location}")
    print_results([reroute])
    city.visualize(reroute.path, "Recalculated A* route after road update", "rerouted_path.png")
    print("\nMaps saved to outputs/initial_route.png and outputs/rerouted_path.png")


if __name__ == "__main__":
    main()
