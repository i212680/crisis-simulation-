from mesa import Model
from mesa.space import MultiGrid
from mesa.time import RandomActivation
from mesa.datacollection import DataCollector
import random
import yaml
from .agents import DroneAgent, MedicAgent, TruckAgent, Survivor

class CrisisModel(Model):
    """A crisis response simulation model with agents, fires, rubble, and hospitals."""
    
    def __init__(self, width, height, rng_seed=42, config=None, render=False):
        super().__init__()
        
        # Initialize random with seed for reproducibility
        self.random = random.Random(rng_seed)
        random.seed(rng_seed)
        
        # Grid and scheduling
        self.width = width
        self.height = height
        self.grid = MultiGrid(width, height, True)
        self.schedule = RandomActivation(self)
        
        # Configuration
        self.config = config or {}
        self.render = render
        
        # Simulation state
        self.time = 0
        self.planned_commands = []
        
        # World state
        self.fires = set()
        self.rubble = set()
        self.hospitals = []
        self.depot = None
        
        # Hospital system
        self.hospital_queues = {}
        self.hospital_service_rate = 0.3  # probability of processing a patient per step
        
        # Metrics
        self.rescued = 0
        self.deaths = 0
        self.fires_extinguished = 0
        self.roads_cleared = 0
        self.energy_used = 0
        self.tool_calls = 0
        self.invalid_json = 0
        self.replans = 0
        self.hospital_overflow_events = 0
        self.total_survivors = 0
        self.rescue_times = []
        
        # Initialize world from config
        self._initialize_world()
        
        # Data collection
        self.datacollector = DataCollector(
            model_reporters={
                "rescued": "rescued",
                "deaths": "deaths",
                "fires_extinguished": "fires_extinguished",
                "roads_cleared": "roads_cleared",
                "energy_used": "energy_used",
                "tool_calls": "tool_calls",
                "invalid_json": "invalid_json",
                "replans": "replans",
                "hospital_overflow_events": "hospital_overflow_events"
            }
        )

    def _initialize_world(self):
        """Initialize the world from configuration."""
        # Set depot
        if "depot" in self.config:
            self.depot = tuple(self.config["depot"])
        
        # Initialize hospitals
        for hospital_pos in self.config.get("hospitals", []):
            pos = tuple(hospital_pos)
            self.hospitals.append(pos)
            self.hospital_queues[pos] = []
        
        # Initialize fires
        for fire_pos in self.config.get("initial_fires", []):
            self.fires.add(tuple(fire_pos))
        
        # Initialize rubble
        for rubble_pos in self.config.get("rubble", []):
            self.rubble.add(tuple(rubble_pos))
        
        # Create survivors
        num_survivors = self.config.get("survivors", 0)
        self.total_survivors = num_survivors
        for i in range(num_survivors):
            # Place survivor at random empty location
            x = self.random.randrange(self.width)
            y = self.random.randrange(self.height)
            # Avoid placing on fires, rubble, hospitals, or depot
            while ((x, y) in self.fires or (x, y) in self.rubble or 
                   (x, y) in self.hospitals or (x, y) == self.depot):
                x = self.random.randrange(self.width)
                y = self.random.randrange(self.height)
            
            survivor = Survivor(f"survivor_{i}", self, health=100.0, spawn_time=self.time)
            self.grid.place_agent(survivor, (x, y))
            self.schedule.add(survivor)
        
        # Create response agents at depot
        if self.depot:
            # Create one of each type of response agent
            drone = DroneAgent("drone_0", self, battery=100.0)
            medic = MedicAgent("medic_0", self, carrying=False)
            truck = TruckAgent("truck_0", self, water=100.0)
            
            for agent in [drone, medic, truck]:
                self.grid.place_agent(agent, self.depot)
                self.schedule.add(agent)

    def set_plan(self, commands):
        """Set the planned commands for the next step."""
        self.planned_commands = commands or []
        self.tool_calls += len(self.planned_commands)

    def step(self):
        """Execute one step of the simulation."""
        self.time += 1
        
        # Execute planned commands
        self._execute_commands()
        
        # Step all agents (survivors check health, etc.)
        self.schedule.step()
        
        # Apply world dynamics
        self._apply_dynamics()
        
        # Process hospitals
        self._process_hospitals()
        
        # Collect data
        self.datacollector.collect(self)

    def _execute_commands(self):
        """Execute the planned commands."""
        for cmd in self.planned_commands:
            try:
                self._execute_single_command(cmd)
            except Exception as e:
                # Count as invalid command
                self.invalid_json += 1
        
        # Clear planned commands
        self.planned_commands = []

    def _execute_single_command(self, cmd):
        """Execute a single command."""
        agent_id = cmd.get("agent_id")
        cmd_type = cmd.get("type")
        
        # Find the agent
        agent = None
        for a in self.schedule.agents:
            if a.unique_id == agent_id:
                agent = a
                break
        
        if agent is None:
            return  # Invalid agent ID
        
        if cmd_type == "move":
            target_pos = cmd.get("to")
            if target_pos and len(target_pos) == 2:
                self._move_agent(agent, tuple(target_pos))
        
        elif cmd_type == "act":
            action_name = cmd.get("action_name")
            if action_name == "extinguish" and isinstance(agent, TruckAgent):
                self._extinguish_fire(agent)
            elif action_name == "pickup_survivor" and isinstance(agent, MedicAgent):
                self._pickup_survivor(agent)
            elif action_name == "drop_at_hospital" and isinstance(agent, MedicAgent):
                self._drop_at_hospital(agent)

    def _move_agent(self, agent, target_pos):
        """Move an agent to target position if valid."""
        x, y = target_pos
        
        # Check bounds
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        
        # Check if blocked by rubble
        if (x, y) in self.rubble:
            return
        
        # Move the agent
        self.grid.move_agent(agent, (x, y))
        
        # Use energy for movement
        if hasattr(agent, 'battery'):
            agent.battery = max(0, agent.battery - 1)
        self.energy_used += 1

    def _extinguish_fire(self, truck_agent):
        """Extinguish fire at truck's current position."""
        pos = truck_agent.pos
        if pos in self.fires and truck_agent.water > 0:
            self.fires.remove(pos)
            truck_agent.water = max(0, truck_agent.water - 10)
            self.fires_extinguished += 1

    def _pickup_survivor(self, medic_agent):
        """Pick up survivor at medic's current position."""
        if medic_agent.carrying:
            return  # Already carrying someone
        
        # Find survivor at same location
        survivors_here = [obj for obj in self.grid.get_cell_list_contents([medic_agent.pos])
                         if isinstance(obj, Survivor) and not getattr(obj, '_picked', False)]
        
        if survivors_here:
            survivor = survivors_here[0]
            survivor._picked = True
            survivor._picked_time = self.time
            medic_agent.carrying = True
            medic_agent.carrying_survivor = survivor

    def _drop_at_hospital(self, medic_agent):
        """Drop survivor at hospital."""
        if not medic_agent.carrying:
            return
        
        pos = medic_agent.pos
        if pos in self.hospitals:
            # Add to hospital queue
            queue = self.hospital_queues.get(pos, [])
            survivor = getattr(medic_agent, 'carrying_survivor', None)
            if survivor:
                queue.append(survivor)
                self.hospital_queues[pos] = queue
                
                # Check for overflow (assuming capacity of 5 per hospital)
                if len(queue) > 5:
                    self.hospital_overflow_events += 1
            
            # Clear medic's carrying status
            medic_agent.carrying = False
            medic_agent.carrying_survivor = None

    def _apply_dynamics(self):
        """Apply world dynamics like fire spread."""
        # Simple fire spread logic
        new_fires = set()
        for fire_pos in list(self.fires):
            x, y = fire_pos
            # 5% chance to spread to adjacent cells
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    
                    nx, ny = x + dx, y + dy
                    if (0 <= nx < self.width and 0 <= ny < self.height and
                        (nx, ny) not in self.fires and (nx, ny) not in self.rubble and
                        self.random.random() < 0.05):
                        new_fires.add((nx, ny))
        
        self.fires.update(new_fires)

    def _process_hospitals(self):
        """Process hospital queues."""
        for hospital_pos, queue in self.hospital_queues.items():
            if queue and self.random.random() < self.hospital_service_rate:
                # Admit one patient
                survivor = queue.pop(0)
                survivor._rescued = True
                self.rescued += 1
                
                # Calculate rescue time
                if hasattr(survivor, '_picked_time'):
                    rescue_time = self.time - survivor._picked_time
                    self.rescue_times.append(rescue_time)

    @property
    def avg_rescue_time(self):
        """Calculate average rescue time."""
        if self.rescue_times:
            return sum(self.rescue_times) / len(self.rescue_times)
        return 0.0

    def summarize_state(self):
        """Summarize the current state for the planner."""
        from .sensors import summarize_state
        return summarize_state(self)