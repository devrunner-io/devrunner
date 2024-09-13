import hashlib
import time

def generate_unique_id():
    # Get the current time in nanoseconds
    current_time = str(time.time_ns())
    
    # Hash the current time to ensure uniqueness and reduce length
    unique_hash = hashlib.sha256(current_time.encode()).hexdigest()
    
    # Take the first 8 characters of the hash (which will be unique)
    unique_id = unique_hash[:8]
    return unique_id