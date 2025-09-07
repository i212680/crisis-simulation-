from mesa import Agent

class DroneAgent(Agent):
    """A drone agent that can scout and provide information."""
    
    def __init__(self, unique_id, model, battery=100.0):
        super().__init__(unique_id, model)
        self.kind = "drone"
        self.battery = battery

    def step(self):
        """Called each simulation step."""
        # Drone logic can be extended
        # For now, just consume some battery
        if self.battery > 0:
            self.battery = max(0, self.battery - 0.5)


class MedicAgent(Agent):
    """A medic agent that can rescue survivors and transport them to hospitals."""
    
    def __init__(self, unique_id, model, carrying=False):
        super().__init__(unique_id, model)
        self.kind = "medic"
        self.carrying = carrying
        self.carrying_survivor = None

    def step(self):
        """Called each simulation step."""
        pass  # Medic logic handled by command execution


class TruckAgent(Agent):
    """A truck agent that can extinguish fires and clear rubble."""
    
    def __init__(self, unique_id, model, water=100.0):
        super().__init__(unique_id, model)
        self.kind = "truck"
        self.water = water

    def step(self):
        """Called each simulation step."""
        pass  # Truck logic handled by command execution


class Survivor(Agent):
    """A survivor that needs to be rescued."""
    
    def __init__(self, unique_id, model, health=100.0, spawn_time=0):
        super().__init__(unique_id, model)
        self.kind = "survivor"
        self.health = health
        self.spawn_time = spawn_time
        self._picked = False
        self._rescued = False
        self._dead = False
        self._picked_time = None

    def step(self):
        """Called each simulation step."""
        # Survivors lose health over time if not rescued
        if not self._picked and not self._rescued and not self._dead:
            self.health -= 1.0
            
            # Die if health reaches 0
            if self.health <= 0:
                self._dead = True
                self.model.deaths += 1