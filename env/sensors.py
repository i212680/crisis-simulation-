"""
Sensors for the crisis simulation.
Provides state summarization for the planner and GUI.
"""

from .agents import DroneAgent, MedicAgent, TruckAgent, Survivor


def summarize_state(model):
    """Summarize the current state for the planner."""
    # Collect agent information
    agents_list = []
    for agent in model.schedule.agents:
        agent_info = {
            "id": agent.unique_id,
            "kind": agent.kind,
            "pos": list(agent.pos) if agent.pos else [0, 0]
        }
        
        # Add agent-specific attributes
        if isinstance(agent, MedicAgent):
            agent_info["carrying"] = getattr(agent, "carrying", False)
        elif isinstance(agent, TruckAgent):
            agent_info["water"] = getattr(agent, "water", 100.0)
        elif isinstance(agent, DroneAgent):
            agent_info["battery"] = getattr(agent, "battery", 100.0)
        elif isinstance(agent, Survivor):
            agent_info["health"] = getattr(agent, "health", 100.0)
            agent_info["picked"] = getattr(agent, "_picked", False)
            agent_info["dead"] = getattr(agent, "_dead", False)
        
        agents_list.append(agent_info)
    
    # Filter survivors for easier access
    survivors_list = []
    for agent in model.schedule.agents:
        if isinstance(agent, Survivor) and not getattr(agent, "_picked", False) and not getattr(agent, "_dead", False):
            survivors_list.append({
                "id": agent.unique_id,
                "pos": list(agent.pos) if agent.pos else [0, 0],
                "health": getattr(agent, "health", 100.0)
            })
    
    # Hospital information
    hospitals_list = []
    for hospital_pos in model.hospitals:
        queue_length = len(model.hospital_queues.get(hospital_pos, []))
        hospitals_list.append({
            "id": f"hospital_{hospital_pos[0]}_{hospital_pos[1]}",
            "pos": list(hospital_pos),
            "capacity": 5,  # Assuming capacity of 5
            "occupied": queue_length
        })
    
    return {
        "tick": model.time,
        "width": model.width,
        "height": model.height,
        "depot": list(model.depot) if model.depot else None,
        "agents": agents_list,
        "survivors": survivors_list,
        "fires": [list(pos) for pos in model.fires],
        "rubble": [list(pos) for pos in model.rubble],
        "hospitals": hospitals_list,
        "metrics": {
            "rescued": model.rescued,
            "deaths": model.deaths,
            "fires_extinguished": model.fires_extinguished,
            "roads_cleared": model.roads_cleared,
            "energy_used": model.energy_used,
            "hospital_overflow_events": model.hospital_overflow_events
        }
    }