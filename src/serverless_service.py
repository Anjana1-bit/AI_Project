"""Stateless routing helpers shared by local and Vercel API handlers."""

from __future__ import annotations

from src.routing_engine import EmergencyRoadNetwork, build_demo_city


def normalize_blocked_roads(blocked_roads: list[dict] | None) -> list[dict]:
    if not isinstance(blocked_roads, list):
        return []
    return [road for road in blocked_roads if isinstance(road, dict) and isinstance(road.get("from"), str) and isinstance(road.get("to"), str)]


def city_for(blocked_roads: list[dict] | None = None) -> EmergencyRoadNetwork:
    city = build_demo_city()
    for road in normalize_blocked_roads(blocked_roads):
        if city.graph.has_edge(road["from"], road["to"]):
            city.update_road(road["from"], road["to"], blocked=True)
    return city


def network_data(blocked_roads: list[dict] | None = None) -> dict:
    city = city_for(blocked_roads)
    return {
        "nodes": [{"name": name, "x": data["pos"][0], "y": data["pos"][1]} for name, data in city.graph.nodes(data=True)],
        "edges": [{"from": a, "to": b, "distance": data["distance"], "traffic": data["traffic"], "blocked": data["blocked"]} for a, b, data in city.graph.edges(data=True)],
    }


def explain_route(city: EmergencyRoadNetwork, path: list[str] | None, algorithm: str) -> list[str]:
    if not path:
        return ["No route was selected because the chosen blocked roads leave no safe connection between these locations."]
    roads = [city.graph[a][b] for a, b in zip(path, path[1:])]
    counts = {level: sum(road["traffic"] == level for road in roads) for level in ("low", "medium", "high")}
    cost = sum(city.edge_cost(a, b) for a, b in zip(path, path[1:]))
    blocked = sum(data["blocked"] for _, _, data in city.graph.edges(data=True))
    first = {
        "astar": "A* selected the route with the lowest traffic-aware utility cost, using travelled cost plus estimated remaining distance.",
        "bfs": "BFS selected a route with the fewest road segments; it does not optimize traffic delay or utility cost.",
        "greedy": "Greedy Best-First Search chose locations that appeared closest to the destination; it does not fully account for travelled cost.",
    }[algorithm]
    traffic_summary = ", ".join(f"{count} {level}-traffic road{'s' if count != 1 else ''}" for level, count in counts.items() if count)
    messages = [first, f"The selected route has {traffic_summary} and a total utility cost of {cost:.2f}."]
    if blocked:
        messages.append(f"{blocked} selected blocked road{' was' if blocked == 1 else 's were'} excluded, so the ambulance is re-routed safely.")
    return messages


def route_data(start: str, destination: str, algorithm: str, blocked_roads: list[dict] | None = None) -> dict:
    city = city_for(blocked_roads)
    choices = {"astar": ("A* (Utility-Aware)", city.astar), "bfs": ("BFS (Fewest Roads)", city.bfs), "greedy": ("Greedy Best-First", city.greedy_best_first)}
    name, search = choices[algorithm]
    result = city.run_algorithm(name, search, start, destination)
    return {"algorithm": result.algorithm, "path": result.path, "distance": None if result.path is None else round(result.distance_km, 1), "minutes": None if result.path is None else round(result.travel_minutes, 1), "utility": None if result.path is None else round(result.utility_cost, 2), "explanation": explain_route(city, result.path, algorithm)}
