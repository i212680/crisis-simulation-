"""
Plan-Execute strategy for crisis simulation.
Implements a simple Chain-of-Thought/Tree-of-Thoughts-like planning approach.
"""

import json


def plan_execute_strategy(context, scratchpad=""):
    """
    Plan-Execute strategy that creates a short-term plan (2-3 steps) for each agent.
    
    Returns a tuple (status, result) where:
    - status: "final" or "thinking"  
    - result: JSON string with commands
    """
    try:
        agents = context.get("agents", [])
        survivors = context.get("survivors", [])
        fires = context.get("fires", [])
        hospitals = context.get("hospitals", [])
        
        # Create a multi-step plan for each agent
        all_commands = []
        
        for agent in agents:
            agent_plan = create_agent_plan(agent, context)
            all_commands.extend(agent_plan)
        
        result = {"commands": all_commands}
        return ("final", json.dumps(result))
    
    except Exception as e:
        # Fallback to empty commands
        return ("final", json.dumps({"commands": []}))


def create_agent_plan(agent, context):
    """Create a multi-step plan for a single agent."""
    agent_kind = agent.get("kind", "")
    agent_pos = agent.get("pos", [0, 0])
    
    if agent_kind == "medic":
        return plan_medic_multi_step(agent, context)
    elif agent_kind == "truck":
        return plan_truck_multi_step(agent, context)
    elif agent_kind == "drone":
        return plan_drone_multi_step(agent, context)
    
    return []


def plan_medic_multi_step(agent, context):
    """Create a 2-3 step plan for a medic agent."""
    commands = []
    agent_pos = agent.get("pos", [0, 0])
    carrying = agent.get("carrying", False)
    
    survivors = context.get("survivors", [])
    hospitals = context.get("hospitals", [])
    
    if carrying:
        # Multi-step plan: move to hospital and drop off
        if hospitals:
            # Find nearest hospital
            nearest_hospital = min(hospitals, 
                                 key=lambda h: manhattan_distance(agent_pos, h["pos"]))
            target_pos = nearest_hospital["pos"]
            
            # Calculate path (simplified to 1-2 steps)
            current_pos = agent_pos[:]
            steps_to_hospital = min(2, manhattan_distance(current_pos, target_pos))
            
            for step in range(steps_to_hospital):
                next_pos = greedy_step(current_pos, target_pos)
                commands.append({
                    "agent_id": agent["id"],
                    "type": "move",
                    "to": next_pos
                })
                current_pos = next_pos
                
                # If we reached the hospital, drop off
                if current_pos == target_pos:
                    commands.append({
                        "agent_id": agent["id"],
                        "type": "act",
                        "action_name": "drop_at_hospital"
                    })
                    break
    else:
        # Multi-step plan: move to survivor and pick up
        if survivors:
            # Find nearest survivor
            nearest_survivor = min(survivors, 
                                 key=lambda s: manhattan_distance(agent_pos, s["pos"]))
            target_pos = nearest_survivor["pos"]
            
            # Calculate path (simplified to 1-2 steps)
            current_pos = agent_pos[:]
            steps_to_survivor = min(2, manhattan_distance(current_pos, target_pos))
            
            for step in range(steps_to_survivor):
                next_pos = greedy_step(current_pos, target_pos)
                commands.append({
                    "agent_id": agent["id"],
                    "type": "move", 
                    "to": next_pos
                })
                current_pos = next_pos
                
                # If we reached the survivor, pick up
                if current_pos == target_pos:
                    commands.append({
                        "agent_id": agent["id"],
                        "type": "act",
                        "action_name": "pickup_survivor"
                    })
                    break
    
    return commands


def plan_truck_multi_step(agent, context):
    """Create a 2-3 step plan for a truck agent."""
    commands = []
    agent_pos = agent.get("pos", [0, 0])
    fires = context.get("fires", [])
    
    if fires:
        # Find nearest fire
        nearest_fire = min(fires, key=lambda f: manhattan_distance(agent_pos, f))
        target_pos = nearest_fire
        
        # Calculate path (simplified to 1-2 steps)
        current_pos = agent_pos[:]
        steps_to_fire = min(2, manhattan_distance(current_pos, target_pos))
        
        for step in range(steps_to_fire):
            next_pos = greedy_step(current_pos, target_pos)
            commands.append({
                "agent_id": agent["id"],
                "type": "move",
                "to": next_pos
            })
            current_pos = next_pos
            
            # If we reached the fire, extinguish
            if current_pos == target_pos:
                commands.append({
                    "agent_id": agent["id"],
                    "type": "act",
                    "action_name": "extinguish"
                })
                break
    
    return commands


def plan_drone_multi_step(agent, context):
    """Create a simple plan for a drone agent."""
    # For now, drones just patrol - could be extended for reconnaissance
    commands = []
    agent_pos = agent.get("pos", [0, 0])
    
    # Simple patrol pattern
    width = context.get("width", 20)
    height = context.get("height", 20)
    
    # Move towards center if at edge, or move randomly
    center_x, center_y = width // 2, height // 2
    
    if abs(agent_pos[0] - center_x) > 5 or abs(agent_pos[1] - center_y) > 5:
        # Move towards center
        next_pos = greedy_step(agent_pos, [center_x, center_y])
        commands.append({
            "agent_id": agent["id"],
            "type": "move",
            "to": next_pos
        })
    
    return commands


def manhattan_distance(pos1, pos2):
    """Calculate Manhattan distance between two positions."""
    return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])


def greedy_step(src, dst):
    """Take one Manhattan step from src towards dst."""
    dx = dst[0] - src[0]
    dy = dst[1] - src[1]
    
    if abs(dx) > abs(dy):
        return [src[0] + (1 if dx > 0 else -1), src[1]]
    elif dy != 0:
        return [src[0], src[1] + (1 if dy > 0 else -1)]
    else:
        return list(src)  # Already at destination