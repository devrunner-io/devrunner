import docker
from fastapi import FastAPI, HTTPException, Request
import psutil
import time
import math
import ipaddress

app = FastAPI()

# Initialize Docker client
client = docker.from_env()

# Add allowed IPs firewall
@app.middleware("http")
async def add_allowed_ips(request: Request, call_next):
    allowed_ips = [
        "127.0.0.1",
        "192.168.0.0/24"
    ]
    
    client_ip = ipaddress.ip_address(request.client.host)

    # Check if the client IP is in the allowed list (support for exact IPs and CIDR ranges)
    if not any(client_ip in ipaddress.ip_network(ip) for ip in allowed_ips):
        # Raise a 403 exception if the IP is not allowed
        raise HTTPException(status_code=403, detail="Forbidden: Your IP is not allowed")

    # Proceed with the request if the IP is allowed
    response = await call_next(request)
    return response

@app.post("/start/{image_name}")
def run_docker(image_name: str):
    try:
        container = client.containers.run(image_name, detach=True)
        
        return {
            "container_id": container.short_id,
            "message": f"Docker container started successfully"}
    except docker.errors.DockerException as e:
        return {"message": f"Failed to start Docker container: {e}"}
    
@app.post("/stop/{container_id}")
def stop_docker(container_id: str):
    try:
        container = client.containers.get(container_id)
        container.stop(timeout=0)
        
        return {"message": f"Docker container {container.short_id} stopped successfully"}
    except docker.errors.DockerException as e:
        return {"message": f"Failed to stop Docker container: {e}"}

@app.get("/system-info")
def get_system_info(Request: Request):
    # Log the IP address of the client
    client_ip = Request.client.host
    print(f"Client IP: {client_ip}")

    cpu_count = psutil.cpu_count()  # Total logical CPUs
    available_memory = psutil.virtual_memory().available / (1024 ** 3)  # Available memory in GB
    real_available_memory = round(available_memory, 2) - 1

    readings = []
    threshold = 20  # CPU usage threshold to consider a core "available"

    # Take 3 readings, logging each one
    for i in range(3):
        cpu_percentages = psutil.cpu_percent(percpu=True)
        available_logical_cores = sum(1 for usage in cpu_percentages if usage < threshold)
        readings.append(available_logical_cores)

        time.sleep(0.05)

    # Calculate the average available logical cores and return the floor of the average
    avg_available_logical_cores = math.floor(sum(readings) / len(readings))
    real_available_cores = avg_available_logical_cores - 1

    return {
        "cpu_count": cpu_count,
        "available_cores": real_available_cores,
        "available_memory": real_available_memory
    }
