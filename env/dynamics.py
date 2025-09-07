"""
World dynamics for the crisis simulation.
Handles fire spread, rubble blocking, resource consumption, hospital intake.
"""

def apply_fire_dynamics(model):
    """Apply fire spread dynamics to the model."""
    new_fires = set()
    
    for fire_pos in list(model.fires):
        x, y = fire_pos
        # Fire has a small chance to spread to adjacent cells
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                
                nx, ny = x + dx, y + dy
                if (0 <= nx < model.width and 0 <= ny < model.height and
                    (nx, ny) not in model.fires and (nx, ny) not in model.rubble and
                    (nx, ny) not in model.hospitals and
                    model.random.random() < 0.02):  # 2% chance per adjacent cell per step
                    new_fires.add((nx, ny))
    
    model.fires.update(new_fires)


def check_rubble_blocking(model, pos):
    """Check if position is blocked by rubble."""
    return pos in model.rubble


def consume_resources(agent, action_type):
    """Consume resources based on action type."""
    if hasattr(agent, 'battery'):
        # Drone uses battery for actions
        if action_type == 'move':
            agent.battery = max(0, agent.battery - 1)
        elif action_type == 'scout':
            agent.battery = max(0, agent.battery - 2)
    
    if hasattr(agent, 'water'):
        # Truck uses water for firefighting
        if action_type == 'extinguish':
            agent.water = max(0, agent.water - 10)


def process_hospital_intake(model):
    """Process hospital intake from queues."""
    for hospital_pos, queue in model.hospital_queues.items():
        # Process one patient per hospital per step with some probability
        if queue and model.random.random() < model.hospital_service_rate:
            survivor = queue.pop(0)
            survivor._rescued = True
            model.rescued += 1
            
            # Track rescue time
            if hasattr(survivor, '_picked_time') and survivor._picked_time is not None:
                rescue_time = model.time - survivor._picked_time
                model.rescue_times.append(rescue_time)