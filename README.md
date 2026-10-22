# AI-Based Emergency Traffic Routing System

A Python microproject for demonstrating an ambulance as a **utility-based intelligent agent**. The agent selects a route that balances travel distance, traffic delay, and road risk, and re-plans when conditions change.

## SDG alignment

- **SDG 3 – Good Health and Well-Being:** faster emergency response can improve access to urgent care.
- **SDG 11 – Sustainable Cities and Communities:** uses traffic-aware routing to support safer, more resilient urban mobility.

## Features

- City represented as a weighted graph (intersections = nodes, roads = edges)
- A* search using straight-line distance as an admissible heuristic
- BFS and Greedy Best-First Search route comparison
- Utility cost based on distance, traffic multiplier, and risk penalty
- Blocked-road handling
- Dynamic re-routing from the ambulance's current position
- Matplotlib map output highlighting the selected route

## Run the front end

The project now includes a basic clickable browser interface with a larger city network. Select the ambulance location, emergency destination, and algorithm, then click **Calculate Route**. Select any road from **Road unavailable in simulation** and click **Block Selected Road**; calculate again to demonstrate re-routing.

The map is intentionally the main screen element. Each route result also includes a concise **Why this route?** explanation that reports the search approach, traffic conditions on the selected roads, utility cost, and any blocked roads avoided.

```bash
source .venv/bin/activate              # Windows: .venv\\Scripts\\activate
python -m src.local_server
```

Then open `http://127.0.0.1:8000` in a browser. Stop the server with `Ctrl+C`.

## Deploy on Vercel

This project is Vercel-ready: `index.html` is the static front end and the `api/` folder contains the required Python serverless handlers. On Vercel, do not use a build command. Import the GitHub repository and deploy it with the default settings.

The simulated traffic update is deliberately stored in the browser request rather than server memory. This is important because Vercel functions are stateless and may be restarted between calls.

## Run the console demo

```bash
python3 -m venv .venv
source .venv/bin/activate              # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python -m src.routing_engine
```

The run prints route comparisons and writes two route-map images to `outputs/`.

## Utility function

For an open road, the agent uses:

```text
road cost = distance × traffic multiplier + risk penalty
estimated time = distance / base speed × traffic multiplier
```

Traffic multipliers are low = 1.0, medium = 1.45, and high = 2.20. Blocked roads are excluded from search. A* minimizes total utility cost; its heuristic is the remaining Euclidean distance, which never overestimates the remaining road cost because every traffic multiplier is at least 1.

## How to demonstrate Module 3

`src/routing_engine.py` begins an ambulance journey from `Hospital` to `Accident Site`. It then changes the network: one road gets heavy traffic and another becomes blocked. The ambulance is assumed to be at `North Junction`, and A* recalculates a new safe route from there. In the browser interface, you choose the road or roads that cannot be used.

You can edit the `apply_dynamic_event()` function or call `network.update_road(...)` to test other events.

## Suggested report discussion points

1. Model the ambulance as a goal-based agent (reach an incident) and then as a utility-based agent (balance time, distance, and risk).
2. Compare the algorithms: BFS optimizes number of roads, Greedy prioritizes apparent closeness to the goal, and A* balances cost already spent with an estimate of what remains.
3. Explain that a real deployment would consume live traffic feeds, GPS locations, and emergency severity data; this project simulates those inputs.
