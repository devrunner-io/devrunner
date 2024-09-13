import argparse
import subprocess
import sys
import textwrap

def build_docker_image(tag, path="."):
    """
    Function to build a Docker image using the specified tag and path.
    """
    try:
        print(f"Building Docker image with tag '{tag}' from path '{path}'...")

        # clean up any existing images if they exist
        subprocess.run(['docker', 'rmi', '-f', tag], capture_output=True)

        # build the image
        subprocess.run(['docker', 'build', '-t', tag, path, '--quiet'], check=True)

        print(f"Docker image '{tag}' built successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error building Docker image: {e}")
        sys.exit(1)

def generate_tag_name(args):
    # get name from the .drconfig file
    with open(".drconfig", "r") as f:
        lines = f.readlines()
        for line in lines:
            if "name" in line:
                project_name = line.split("=")[1].strip()
                break

    # return the tag name
    return f"devrunner-{project_name}-worker"

def push_docker_image(tag):
    """
    Pushes a Docker image to the remote registry.
    """
    print(f"Pushing Docker image with tag: {tag}")
    subprocess.run(["docker", "push", tag], check=True)

def deploy(args):
    """
    Deploy command to build Docker images.
    """

    tag = args.tag if args.tag else generate_tag_name(args)

    full_tag = f"cr.devrunner.io/testing:{tag}"

    build_docker_image(tag=full_tag, path=args.path)
    push_docker_image(full_tag)

def worker(args):
    """
    Run command to run Docker containers.
    """

    if not args.tag:
        # get the tag from the .drconfig file
        with open(".drconfig", "r") as f:
            lines = f.readlines()
            for line in lines:
                if "name" in line:
                    project_name = line.split("=")[1].strip()
                    break
    
        tag = f"devrunner-{project_name}-worker"
    else:
        tag = args.tag

    print(f"running worker '{tag}'...")
    subprocess.run(['docker', 'run', tag], check=True)

def create_project(args):
    # create a directory with the project name
    project_name = args.name

    # stop if the directory already exists
    if subprocess.run(['ls', project_name], capture_output=True).returncode == 0:
        if not args.replace:
            print(f"Project {project_name} already exists!")
            sys.exit(1)
        else:
            subprocess.run(['rm', '-rf', project_name])

    # check the name doesn't exist
    subprocess.run(['mkdir', project_name])
    # create a Dockerfile with comments

    python_version = "3.11"

    dockerfile = textwrap.dedent(f"""\
        FROM python:{python_version}-slim
        
        # Set the working directory
        WORKDIR /{project_name}
        
        # Copy the current directory contents into the container at /app
        COPY {project_name} /{project_name}
        
        # Install the dependencies
        RUN pip install --no-cache-dir -r requirements.txt
        
        # Expose port 80
        EXPOSE 80
        
        # Define the command to run the application
        CMD ["python", "app.py"]
    """)

    with open(f"Dockerfile", "w") as f:
        f.write(dockerfile)

    # create an empty requirements.txt
    with open(f"{project_name}/requirements.txt", "w") as f:
        f.write("")
    
    # create app.py with no extra indentation
    app_py = textwrap.dedent("""\
        import time
                             
        def main():
            for i in range(10):
                print(f"{i}")
                time.sleep(0.3)
        
        if __name__ == "__main__":
            main()
    """)

    with open(f"{project_name}/app.py", "w") as f:
        f.write(app_py)

    # create a .drconfig file with the project name and python version
    drconfig = textwrap.dedent(f"""\
        [project]
        name = {project_name}
        python_version = {python_version}
        memory_limit = 512M
        cpu_limit = 0.5
    """)

    with open(f".drconfig", "w") as f:
        f.write(drconfig)
    
    print(f"Created {project_name}")

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

def main():
    parser = argparse.ArgumentParser(prog="devrunner", description="Deploy and run Docker containers.")
    subparsers = parser.add_subparsers(title="commands", description="Available commands", help="Sub-command help")
    
    # Define the 'deploy' command
    parser_deploy = subparsers.add_parser("deploy", help="Build Docker image.")
    parser_deploy.add_argument("-t", "--tag", required=False, help="Tag for the Docker image.")
    parser_deploy.add_argument("-p", "--path", default=".", help="Path to the Dockerfile directory (default is current directory).")
    parser_deploy.set_defaults(func=deploy)
    
    # # Define the 'run' command
    parser_run = subparsers.add_parser("execute", help="Run Docker container.")
    parser_run.add_argument("-t", "--tag", required=False, help="Tag of the Docker image to run.")
    parser_run.set_defaults(func=worker)

    parser_id = subparsers.add_parser("create", help="create a deployment project")
    parser_id.add_argument("-n", "--name", required=True, help="Name of the project")
    parser_id.add_argument("-r", "--replace", action="store_true", help="Replaces the project if it already exists")
    parser_id.set_defaults(func=create_project)

    parser_server = subparsers.add_parser("ready", help="Start the server")
    parser_server.add_argument("-p", "--port", default=8000, type=int, help="Port to run the server on")
    parser_server.set_defaults(func=start_server)

    parser_stop = subparsers.add_parser("stop", help="Stop the server")
    parser_stop.set_defaults(func=stop_server)

    # Parse the arguments and call the respective function
    args = parser.parse_args()

    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()