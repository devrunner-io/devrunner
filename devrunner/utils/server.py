import subprocess
import sys


def start_server(args):
    port = str(args.port)
    
    # Check if the port is already in use
    try:
        subprocess.check_output(['lsof', '-t', f'-i:{port}'])
        # If lsof returns output, it means the port is in use
        print(f"Error: Port {port} is already in use. Cannot start server.")
        sys.exit(1)  # Exit with error code
    except subprocess.CalledProcessError:
        # If lsof raises an error, it means the port is not in use, so we can start the server
        subprocess.Popen(
            ['uvicorn', 'devrunner.server.server:app', '--reload', '--host', '0.0.0.0', '--port', port],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        print(f"devrunner is ready to accept requests on port {port}")

def stop_server(args):

    try:
        # Use pgrep to find uvicorn processes that are using the specified port
        pids = subprocess.check_output(['pgrep', '-fl', 'uvicorn']).decode().strip().split('\n')

        uvicorn_pids = []
        ports = []
        for process_info in pids:
            if f'devrunner' in process_info:
                pid = process_info.split()[0]  # The first part of the output is the PID
                uvicorn_pids.append(pid)
                ports.append(process_info.split()[-1])  # The last part of the output is the port
        
        if not uvicorn_pids:
            print(f"No uvicorn server running.")
            return

        # Kill each uvicorn process individually
        for uvicorn_pid, port in zip(uvicorn_pids, ports):
            subprocess.run(['kill', uvicorn_pid])
            print(f"devrunner listener on port {port} was terminated.")
    
    except subprocess.CalledProcessError:
        print(f"No uvicorn server running on port '{port}'.")
