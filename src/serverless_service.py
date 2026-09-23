"""Stateless helpers shared by the Vercel API functions.

Vercel functions can be started or stopped between requests. The browser therefore
sends the current simulation state (``updated``) with each request, and this module
rebuilds the small demonstration network deterministically.
"""

from __future__ import annotations

from src.routing_engine import EmergencyRoadNetwork, apply_dynamic_event, build_demo_city


def city_for(updated: bool = False) -> EmergencyRoadNetwork:
    city = build_demo_city()
    if updated:
        apply_dynamic_event(city)
    return city


def network_data(updated: bool = False) -> dict:
    city = city_for(updated)
    return {
        "nodes": [{"name": name, "x": data["pos"][0], "y": data["pos"][1]} for name, data in city.graph.nodes(data=True)],
        "edges": [
            {"from": a, "to": b, "distance": data["distance"], "traffic": data["traffic"], "blocked": data["blocked"]}
            for a, b, data in city.graph.edges(data=True)
        ],
        "updated": updated,
    }


def explain_route(city: EmergencyRoadNetwork, path: list[str] | None, algorithm: str) -> list[str]:
    if not path:
        return ["No route was selected because there is no open path between these locations."]
    roads = [city.graph[a][b] for a, b in zip(path, path[1:])]
    counts = {level: sum(road["traffic"] == level for road in roads) for level in ("low", "medium", "high")}
    cost = sum(city.edge_cost(a, b) for a, b in zip(path, path[1:]))
    blocked = sum(data["blocked"] for _, _, data in city.graph.edges(data=True))
    algorithm_message = {
        "astar": "A* selected the route with the lowest traffic-aware utility cost. It combines the cost already travelled with an estimate of the remaining distance.",
        "bfs": "BFS selected this route because it uses the fewest road segments. It does not optimize traffic delay or utility cost.",
        "greedy": "Greedy Best-First Search selected locations that appeared closest to the destination. It does not fully account for the cost already travelled.",
    }[algorithm]
    traffic_summary = ", ".join(f"{count} {level}-traffic road{'s' if count != 1 else ''}" for level, count in counts.items() if count)
    messages = [algorithm_message, f"The chosen path contains {traffic_summary} and has a total utility cost of {cost:.2f}."]
    if blocked:
        messages.append(f"{blocked} blocked road{' was' if blocked == 1 else 's were'} excluded automatically, so the ambulance is not routed through an unsafe road.")
    messages.append(
        "The route avoids high-traffic roads, helping reduce estimated emergency response time."
        if counts["high"] == 0
        else "A high-traffic road remains only because it is part of the best available path under the current road conditions."
    )
    return messages


def route_data(start: str, destination: str, algorithm: str, updated: bool = False) -> dict:
    city = city_for(updated)
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
        "explanation": explain_route(city, result.path, algorithm),
    }
