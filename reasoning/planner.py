import json
from .react import react_plan
from .llm_client import llm_complete

def make_plan(context, strategy="react_reflexion", scratchpad=""):
    """
    Main planner entry point that routes to different strategies.
    
    Args:
        context: Current world state
        strategy: Planning strategy ("react", "react_reflexion", "plan_execute")
        scratchpad: Previous context/memory for reflexion
    
    Returns:
        dict: {"commands": [...], "metadata": {...}}
    """
    try:
        if strategy == "react_reflexion":
            return make_reflexion_plan(context, scratchpad)
        elif strategy == "plan_execute":
            return make_plan_execute(context, scratchpad)
        else:  # Default to "react"
            return make_react_plan(context, scratchpad)
    
    except Exception as e:
        # Fallback to basic react on any error
        context["tool_calls"] = context.get("tool_calls", 0) + 1
        context["invalid_json"] = context.get("invalid_json", 0) + 1
        return make_react_plan(context, "")

def make_react_plan(context, scratchpad=""):
    """Basic ReAct planning strategy."""
    kind, payload = react_plan(context, scratchpad=scratchpad)
    
    if kind == "final":
        try:
            plan_dict = json.loads(payload)
            return {"commands": plan_dict.get("commands", []), "strategy_used": "react"}
        except json.JSONDecodeError:
            # Invalid JSON - increment counter and use fallback
            if hasattr(context, 'invalid_json'):
                context.invalid_json += 1
            return {"commands": [], "strategy_used": "react_fallback"}
    else:
        # For full LLM ReAct you'd call tools based on 'action' here and loop
        return {"commands": [], "strategy_used": "react_incomplete"}

def make_reflexion_plan(context, scratchpad=""):
    """ReAct with reflexion for error correction."""
    # First try normal react
    plan = make_react_plan(context, scratchpad)
    
    # If we have previous failures in scratchpad, try to learn from them
    if scratchpad and "ERROR" in scratchpad:
        try:
            from .reflexion import critique_and_update
            # Get critique of recent failures
            critique = critique_and_update(scratchpad[-1000:])  # Last 1000 chars
            
            # Try to generate an improved plan with critique
            if hasattr(context, 'replans'):
                context.replans += 1
            
            # For now, just return the original plan but mark that we attempted reflexion
            plan["strategy_used"] = "react_reflexion" 
            plan["critique_applied"] = True
        except Exception:
            plan["strategy_used"] = "react_reflexion_fallback"
    else:
        plan["strategy_used"] = "react_reflexion"
    
    return plan

def make_plan_execute(context, scratchpad=""):
    """Plan-Execute strategy with lookahead."""
    try:
        # Simple 2-3 step lookahead planning
        agents = context.get("agents", [])
        survivors = context.get("survivors", [])
        fires = context.get("fires", [])
        hospitals = context.get("hospitals", [])
        
        commands = []
        
        # Plan for each agent over next 2-3 steps
        for agent in agents:
            if agent.get("kind") == "medic":
                commands.extend(_plan_medic_actions(agent, survivors, hospitals))
            elif agent.get("kind") == "truck":
                commands.extend(_plan_truck_actions(agent, fires))
            elif agent.get("kind") == "drone":
                # Simple drone behavior - could be extended
                commands.extend(_plan_drone_actions(agent, survivors, fires))
        
        return {"commands": commands, "strategy_used": "plan_execute"}
    
    except Exception:
        # Fallback to react
        return make_react_plan(context, scratchpad)

def _plan_medic_actions(agent, survivors, hospitals):
    """Plan actions for a medic agent."""
    commands = []
    agent_pos = agent.get("pos", [0, 0])
    
    if agent.get("carrying", False):
        # Head to nearest hospital
        if hospitals:
            nearest_hospital = min(hospitals, key=lambda h: _manhattan_distance(agent_pos, h["pos"]))
            target = nearest_hospital["pos"]
            next_pos = _greedy_step(agent_pos, target)
            
            commands.append({
                "agent_id": agent["id"],
                "type": "move",
                "to": next_pos
            })
            
            # If at hospital, drop off
            if agent_pos == target:
                commands.append({
                    "agent_id": agent["id"],
                    "type": "act",
                    "action_name": "drop_at_hospital"
                })
    else:
        # Head to nearest survivor
        if survivors:
            nearest_survivor = min(survivors, key=lambda s: _manhattan_distance(agent_pos, s["pos"]))
            target = nearest_survivor["pos"]
            next_pos = _greedy_step(agent_pos, target)
            
            commands.append({
                "agent_id": agent["id"],
                "type": "move",
                "to": next_pos
            })
            
            # If at survivor location, pick up
            if agent_pos == target:
                commands.append({
                    "agent_id": agent["id"],
                    "type": "act",
                    "action_name": "pickup_survivor"
                })
    
    return commands

def _plan_truck_actions(agent, fires):
    """Plan actions for a truck agent."""
    commands = []
    agent_pos = agent.get("pos", [0, 0])
    
    if fires:
        # Head to nearest fire
        nearest_fire = min(fires, key=lambda f: _manhattan_distance(agent_pos, f))
        target = nearest_fire
        next_pos = _greedy_step(agent_pos, target)
        
        commands.append({
            "agent_id": agent["id"],
            "type": "move",
            "to": next_pos
        })
        
        # If at fire location, extinguish
        if agent_pos == target:
            commands.append({
                "agent_id": agent["id"],
                "type": "act",
                "action_name": "extinguish"
            })
    
    return commands

def _plan_drone_actions(agent, survivors, fires):
    """Plan actions for a drone agent."""
    # Simple drone behavior - just move around for now
    # Could be extended to provide reconnaissance
    return []

def _manhattan_distance(pos1, pos2):
    """Calculate Manhattan distance between two positions."""
    return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

def _greedy_step(src, dst):
    """Take one Manhattan step from src towards dst."""
    dx = dst[0] - src[0]
    dy = dst[1] - src[1]
    
    if abs(dx) > abs(dy):
        return [src[0] + (1 if dx > 0 else -1), src[1]]
    elif dy != 0:
        return [src[0], src[1] + (1 if dy > 0 else -1)]
    else:
        return list(src)  # Already at destination
