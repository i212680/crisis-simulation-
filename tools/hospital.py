"""
Hospital triage system for crisis simulation.
Manages hospital queues, capacity, and patient processing.
"""

def hospital_queue_state(model):
    """Get the current state of all hospital queues."""
    return {
        "queues": [{"hospital": list(k), "len": len(v)} for k,v in model.hospital_queues.items()],
        "service_rate": model.hospital_service_rate
    }

def admit_patient(model, hospital_pos, patient):
    """Admit a patient to a hospital queue."""
    if hospital_pos in model.hospital_queues:
        queue = model.hospital_queues[hospital_pos]
        queue.append(patient)
        
        # Check for overflow (capacity is assumed to be 5)
        if len(queue) > 5:
            model.hospital_overflow_events += 1
            return False  # Overflow occurred
        return True  # Successfully admitted
    return False  # Invalid hospital

def discharge_patients(model):
    """Process hospital queues and discharge patients."""
    discharged = 0
    
    for hospital_pos, queue in model.hospital_queues.items():
        if queue and model.random.random() < model.hospital_service_rate:
            # Discharge one patient
            patient = queue.pop(0)
            patient._rescued = True
            model.rescued += 1
            discharged += 1
            
            # Track rescue time if available
            if hasattr(patient, '_picked_time') and patient._picked_time is not None:
                rescue_time = model.time - patient._picked_time
                model.rescue_times.append(rescue_time)
    
    return discharged

def get_hospital_capacity_info(model):
    """Get capacity information for all hospitals."""
    info = {}
    for hospital_pos in model.hospitals:
        queue_len = len(model.hospital_queues.get(hospital_pos, []))
        info[hospital_pos] = {
            "current_queue": queue_len,
            "capacity": 5,
            "available": max(0, 5 - queue_len),
            "is_full": queue_len >= 5
        }
    return info
