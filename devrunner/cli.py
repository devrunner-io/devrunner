import argparse
from .utils import *
from getpass import getpass
import requests

import os
import json
import stat
import platform

# Generic store function
def store_data(file_name, data):
    home_dir = os.path.expanduser("~")
    file_path = os.path.join(home_dir, ".devrunner", file_name)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # Write the data to the file
    with open(file_path, 'w') as f:
        json.dump(data, f)

    # Set file permissions: read/write for the user only (for Linux/macOS)
    if platform.system() != "Windows":
        os.chmod(file_path, 0o600)
    else:
        os.chmod(file_path, stat.S_IWRITE)  # Ensure it's writable for Windows

# Generic delete function
def delete_data(file_name):
    file_path = os.path.expanduser(f"~/.devrunner/{file_name}")
    if os.path.exists(file_path):
        os.remove(file_path)

# Reuse store_data and delete_data for tokens and other user data
def store_access_token(token):
    store_data("__a_t__.json", {"token": token})

def store_refresh_token(token):
    store_data("__r_t__.json", {"token": token})

def store_email(email):
    store_data("__e__.json", {"token": email})

def get_data(file_name):
    file_path = os.path.expanduser(f"~/.devrunner/{file_name}")
    if os.path.exists(file_path):
        with open(file_path) as f:
            return json.load(f).get("token")
    return None

def get_access_token():
    return get_data("__a_t__.json")

def get_refresh_token():
    return get_data("__r_t__.json")

def get_email():
    return get_data("__e__.json")

def delete_access_token():
    delete_data("__a_t__.json")

def delete_refresh_token():
    delete_data("__r_t__.json")

def refresh_token():
    response = requests.post(
        "http://localhost:8000/refresh-token",
        cookies={"refresh_token": get_refresh_token()}
    )

    if response.status_code == 200:
        store_access_token(response.json().get("token"))
        store_refresh_token(response.cookies.get("refresh_token"))
        return True

    return False

def login(args):
    token = get_access_token()

    if token:
        response = requests.get(
            "http://localhost:8000/check-token",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code == 200:
            print("You are already logged in.")
            return
        elif response.status_code == 401:
            delete_access_token()

    if refresh_token():
        print("You are already logged in.")
        return

    existing_email = get_email()
    if existing_email:
        email = input(f"Email ({existing_email}): ") or existing_email
    else:
        email = input("Email: ")
    password = getpass("Password: ")

    response = requests.post(
        "http://localhost:8000/login",
        json={"email": email, "password": password}
    )

    if response.status_code == 200:
        print("Login successful.")
        store_access_token(response.json().get("token"))
        store_refresh_token(response.cookies.get("refresh_token"))
        store_email(email)
    else:
        print("Login failed.")
    return response.json()

def logout(args):
    delete_access_token()
    delete_refresh_token()
    print("Logged out successfully.")

def main():
    parser = argparse.ArgumentParser(prog="devrunner", description="Deploy and run Docker containers.")
    subparsers = parser.add_subparsers(title="commands", description="Available commands", help="Sub-command help")

    parser_login = subparsers.add_parser("login", help="Login to devrunner.")
    parser_login.set_defaults(func=login)

    parser_logout = subparsers.add_parser("logout", help="Logout from devrunner.")
    parser_logout.set_defaults(func=logout)

    parser_deploy = subparsers.add_parser("deploy", help="Build Docker image.")
    parser_deploy.add_argument("-p", "--path", default=".", help="Path to the Dockerfile directory (default is current directory).")
    parser_deploy.set_defaults(func=deploy)

    parser_run = subparsers.add_parser("execute", help="Run Docker container.")
    parser_run.add_argument("-t", "--tag", required=False, help="Tag of the Docker image to run.")
    parser_run.set_defaults(func=execute)

    parser_id = subparsers.add_parser("create", help="create a deployment project")
    parser_id.add_argument("-n", "--name", required=True, help="Name of the project")
    parser_id.add_argument("-r", "--replace", action="store_true", help="Replaces the project if it already exists")
    parser_id.add_argument('python_version', type=str, default="python==3.12", help="Specify the Python version (e.g., python==3.12)")
    parser_id.set_defaults(func=create_project)

    parser_server = subparsers.add_parser("ready", help="Start the server")
    parser_server.add_argument("-p", "--port", default=8000, type=int, help="Port to run the server on")
    parser_server.set_defaults(func=start_server)

    parser_stop = subparsers.add_parser("stop", help="Stop the server")
    parser_stop.set_defaults(func=stop_server)

    args = parser.parse_args()

    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
