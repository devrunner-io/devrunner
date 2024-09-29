import subprocess
import sys


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

def build_tag_name(args):
    # get name from the .drconfig file
    image_name = None
    namespace = None
    with open(".drconfig", "r") as f:
        lines = f.readlines()
        for line in lines:
            if "image_name" in line:
                image_name = line.split("=")[1].strip()
                
            if "namespace" in line:
                namespace = line.split("=")[1].strip()

    if not namespace:
        raise ValueError("Namespace not found in .drconfig file")
    
    if not image_name:
        raise ValueError("Project name not found in .drconfig file")

    return f"{namespace}/{image_name}"

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

    tag = build_tag_name(args)
    full_tag = f"cr.devrunner.io/{tag}:latest"

    build_docker_image(tag=full_tag, path=args.path)
    push_docker_image(full_tag)

def execute(args):
    """
    Run command to run Docker containers.
    """
    tag = build_tag_name(args)

    print(f"running worker '{tag}'...")
    subprocess.run(['docker', 'run', tag], check=True)