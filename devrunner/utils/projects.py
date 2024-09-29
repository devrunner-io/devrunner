import subprocess
import sys
import textwrap


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
    
    python_version = args.python_version.split("==")[1]

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