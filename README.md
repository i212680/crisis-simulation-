# CrisisSim - Mesa-Based Crisis Response Simulation

A crisis response simulation with agentic planning featuring multiple agents (trucks, medics, drones) responding to fires, rescuing survivors, and managing hospital capacity in real-time.

![CrisisSim GUI](https://github.com/user-attachments/assets/1bb746e0-dd2c-49f1-a3a9-4cf315c7797d)

## Quickstart

```bash
# Install dependencies
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Run single episode (mock mode - no API keys needed)
python main.py --map configs/map_small.yaml --provider mock --strategy react_reflexion --seed 42 --ticks 150

# Launch GUI
python server.py     # open http://127.0.0.1:8521

# Batch evaluation
python eval/harness.py --n_seeds 3 --maps configs/map_small.yaml configs/map_hard.yaml --conditions react_reflexion_mock

# Generate plots
python eval/plots.py --input results --out results/plots
```

## Real LLMs (Optional)

```bash
# Groq
export LLM_PROVIDER=groq
export GROQ_API_KEY=YOUR_KEY

# Gemini  
export LLM_PROVIDER=gemini
export GEMINI_API_KEY=YOUR_KEY
```

## Architecture

```
crisis-simulation/
├── env/              # Mesa world, agents, dynamics, sensors  
│   ├── world.py      # CrisisModel - main simulation
│   ├── agents.py     # DroneAgent, MedicAgent, TruckAgent, Survivor
│   ├── dynamics.py   # Fire spread, resource consumption
│   └── sensors.py    # State summarization for planner
├── reasoning/        # Planning strategies
│   ├── planner.py    # Strategy router and orchestration
│   ├── react.py      # Mock ReAct baseline 
│   ├── reflexion.py  # Self-critique and replanning
│   ├── plan_execute.py # Lookahead planning strategy
│   └── llm_client.py # LLM provider abstraction
├── tools/            # Utilities
│   ├── routing.py    # A* pathfinding
│   ├── resources.py  # Resource tracking
│   └── hospital.py   # Triage queues and capacity
├── configs/          # Scenario definitions
│   ├── map_small.yaml
│   ├── map_medium.yaml
│   └── map_hard.yaml
└── eval/             # Evaluation pipeline
    ├── harness.py    # Batch experiment runner
    └── plots.py      # Results visualization
```

## Planning Strategies

- **`react`**: Basic mock heuristic planning (medics→survivors→hospitals, trucks→fires)
- **`react_reflexion`**: React with error critique and memory
- **`plan_execute`**: Multi-step lookahead planning (2-3 step horizon)

## Maps & Scenarios

- **`map_small.yaml`**: 20×20 grid, 15 survivors, 2 hospitals, moderate complexity
- **`map_medium.yaml`**: 25×25 grid, 20 survivors, 3 hospitals, increased challenge  
- **`map_hard.yaml`**: 20×20 grid, 25 survivors, 2 hospitals, high density

## Metrics Tracked

- `rescued`: Survivors admitted to hospitals
- `deaths`: Survivors who died before rescue
- `fires_extinguished`: Fires put out by trucks
- `roads_cleared`: Rubble cleared (future extension)
- `energy_used`: Total energy consumed by agents
- `tool_calls`: Number of commands executed
- `invalid_json`: Failed command parses
- `replans`: Strategy replanning attempts
- `hospital_overflow_events`: Hospital capacity exceeded
- `avg_rescue_time`: Average time from pickup to hospital admission

## GUI Features

- **Real-time visualization**: Grid with agents, fires, survivors, hospitals
- **Interactive controls**: Start/Stop/Step/Reset simulation
- **Live charts**: Rescued, deaths, fires extinguished over time
- **Statistics panel**: Current counts and progress metrics

## Evaluation Pipeline

```bash
# Run multiple seeds and conditions
python eval/harness.py --n_seeds 5 --maps configs/map_small.yaml --conditions react_mock react_reflexion_mock

# Results saved to results/*.csv with crisis_score calculated as:
# crisis_score = 3×rescued - 2×deaths + 1×fires_extinguished + 0.5×roads_cleared - 0.1×energy_used - 0.05×hospital_overflow
```

## Development & Extension

The simulation is designed to be easily extensible:

- **Add new agent types**: Inherit from `Agent` in `env/agents.py`
- **New planning strategies**: Add to `reasoning/planner.py` 
- **Custom dynamics**: Extend `env/dynamics.py`
- **New metrics**: Update `DataCollector` in `env/world.py`

## Requirements

- Python 3.9+
- Mesa 2.1.5 (agent-based modeling)
- NumPy, Pandas, Matplotlib (data & visualization)
- Optional: Groq, Google Generative AI (for real LLM planning)
