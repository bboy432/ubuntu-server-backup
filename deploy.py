import getpass
import os
import paramiko
import time

# --- Configuration ---
# The local path to the new application code that will be deployed.
LOCAL_SOURCE_PATH = "/home/server/Desktop/1.1.6 (final cleanup)/"
# The destination path on the remote server where the new app will be placed.
REMOTE_DEST_PATH = "/srv/warm_transfer_app"
# The name of the new systemd service for the application.
NEW_SERVICE_NAME = "warm_transfer.service"


def print_header(title):
    """Prints a formatted header to the console."""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)


def get_ssh_client():
    """
    Prompts user for credentials and returns a connected Paramiko SSH client.
    """
    print_header("1. Connect to Remote Server")
    ip = input("Enter the remote server IP address: ")
    username = input("Enter the username: ")
    password = getpass.getpass("Enter the password: ")

    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        print(f"Connecting to {username}@{ip}...")
        client.connect(ip, username=username, password=password, timeout=10)
        print("Connection successful!")
        return client
    except Exception as e:
        print(f"Error connecting to server: {e}")
        return None


def run_remote_command(client, command, description):
    """
    Runs a command on the remote server, printing its status and output.
    Returns True on success, False on failure.
    """
    print(f"\n--> {description}...")
    try:
        stdin, stdout, stderr = client.exec_command(command, get_pty=True)
        # We must read the output for the command to complete.
        exit_code = stdout.channel.recv_exit_status()
        output = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')

        if exit_code == 0:
            print("    Status: SUCCESS")
            if output:
                print(f"    Output:\n{output}")
            return True
        else:
            print(f"    Status: FAILED (Exit Code: {exit_code})")
            if output:
                print(f"    Output:\n{output}")
            if error:
                print(f"    Error:\n{error}")
            return False
    except Exception as e:
        print(f"    An exception occurred: {e}")
        return False


def clean_old_application(client):
    """Removes the old application and its service."""
    print_header("2. Clean Up Old Application")
    old_app_path = input("Enter the absolute path of the OLD application directory to delete: ")
    old_service_name = input("Enter the name of the OLD systemd service to stop and disable: ")

    if not old_app_path or not old_service_name:
        print("Skipping cleanup: No path or service name provided.")
        return

    run_remote_command(client, f"sudo systemctl stop {old_service_name}", f"Stopping old service ({old_service_name})")
    run_remote_command(client, f"sudo systemctl disable {old_service_name}", f"Disabling old service ({old_service_name})")
    run_remote_command(client, f"sudo rm -f /etc/systemd/system/{old_service_name}", "Removing old service file")
    run_remote_command(client, "sudo systemctl daemon-reload", "Reloading systemd daemon")
    run_remote_command(client, f"sudo rm -rf {old_app_path}", f"Deleting old application directory ({old_app_path})")


def deploy_new_application(client):
    """Uploads the new application files."""
    print_header("3. Deploy New Application")
    
    # Create remote directory
    if not run_remote_command(client, f"sudo mkdir -p {REMOTE_DEST_PATH}", f"Creating remote directory ({REMOTE_DEST_PATH})"):
        return False
    if not run_remote_command(client, f"sudo chown -R {client.get_transport().get_username()}:{client.get_transport().get_username()} {REMOTE_DEST_PATH}", "Setting directory ownership"):
        return False

    # Upload files
    print(f"\n--> Uploading application files to {REMOTE_DEST_PATH}...")
    try:
        sftp = client.open_sftp()
        for root, dirs, files in os.walk(LOCAL_SOURCE_PATH):
            # Create corresponding remote directories
            remote_root = os.path.join(REMOTE_DEST_PATH, os.path.relpath(root, LOCAL_SOURCE_PATH)).replace("\\", "/")
            for dir_name in dirs:
                remote_dir_path = f"{remote_root}/{dir_name}"
                try:
                    sftp.stat(remote_dir_path)
                except FileNotFoundError:
                    print(f"    Creating remote subdirectory: {remote_dir_path}")
                    sftp.mkdir(remote_dir_path)

            # Upload files
            for file_name in files:
                local_file_path = os.path.join(root, file_name)
                remote_file_path = os.path.join(REMOTE_DEST_PATH, os.path.relpath(local_file_path, LOCAL_SOURCE_PATH)).replace("\\", "/")
                print(f"    Uploading: {os.path.relpath(local_file_path, LOCAL_SOURCE_PATH)} -> {remote_file_path}")
                sftp.put(local_file_path, remote_file_path)
        sftp.close()
        print("    Status: SUCCESS")
        return True
    except Exception as e:
        print(f"    File upload failed: {e}")
        return False


def setup_environment_and_service(client):
    """Installs dependencies and creates/enables the new systemd service."""
    print_header("4. Set Up Environment and Service")

    # Update and install dependencies
    run_remote_command(client, "sudo apt-get update", "Updating package lists")
    run_remote_command(client, "sudo apt-get install -y python3-pip", "Ensuring pip is installed")
    run_remote_command(client, f"sudo pip3 install -r {REMOTE_DEST_PATH}/requirements.txt", "Installing app dependencies")

    # Create systemd service file
    service_content = f"""
[Unit]
Description=Warm Transfer Webhook Service
After=network.target

[Service]
User={client.get_transport().get_username()}
WorkingDirectory={REMOTE_DEST_PATH}
ExecStart=/usr/bin/python3 {REMOTE_DEST_PATH}/transfer.py
Restart=always

[Install]
WantedBy=multi-user.target
"""
    remote_service_path = f"/tmp/{NEW_SERVICE_NAME}"
    print(f"\n--> Creating new systemd service file ({NEW_SERVICE_NAME})...")
    try:
        sftp = client.open_sftp()
        with sftp.file(remote_service_path, 'w') as f:
            f.write(service_content)
        sftp.close()
        print("    Status: SUCCESS (Temp file created)")
    except Exception as e:
        print(f"    FAILED to create temp service file: {e}")
        return

    run_remote_command(client, f"sudo mv {remote_service_path} /etc/systemd/system/{NEW_SERVICE_NAME}", "Moving service file to systemd directory")
    
    # Enable and start the new service
    run_remote_command(client, "sudo systemctl daemon-reload", "Reloading systemd daemon")
    run_remote_command(client, f"sudo systemctl enable {NEW_SERVICE_NAME}", f"Enabling new service ({NEW_SERVICE_NAME})")
    run_remote_command(client, f"sudo systemctl start {NEW_SERVICE_NAME}", "Starting new service")
    time.sleep(3) # Give service time to start
    run_remote_command(client, f"sudo systemctl status {NEW_SERVICE_NAME}", "Checking service status")


def main():
    """Main function to run the deployment process."""
    client = get_ssh_client()
    if not client:
        return

    try:
        clean_old_application(client)
        if deploy_new_application(client):
            setup_environment_and_service(client)
    finally:
        print("\n" + "="*60)
        print(" Deployment script finished. Closing connection.")
        print("="*60)
        client.close()


if __name__ == "__main__":
    main()
