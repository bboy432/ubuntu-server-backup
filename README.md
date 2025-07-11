# Remote Application Deployment Script

This Python script automates the deployment of the "Warm Transfer" application to a remote Ubuntu server. It is designed to be a safe replacement for manual deployment, handling cleanup, file transfer, and service setup.

**WARNING:** This script performs administrative actions on a remote server, including file deletion. Use it with extreme caution. Always double-check the information you provide to the script.

## Features

-   Connects to a remote Ubuntu server over SSH.
-   Safely cleans up a previous version of the application by stopping its service and deleting its directory.
-   Transfers the new application files to the server.
-   Updates the server's package list.
-   Installs the required Python packages for the application.
-   Sets up and enables a `systemd` service to ensure the application runs automatically on boot.

## How to Use

### 1. Prerequisites

This script is designed to be run from your local machine (like your desktop), not from the server itself.

-   You must have Python 3 and `pip` installed on your local machine.
-   The remote server must be an Ubuntu server with SSH access enabled.

### 2. Installation

Before running the script for the first time, you need to install its only dependency, `paramiko`.

Navigate to the `code_pusher` directory in your terminal and run:

```bash
pip install -r requirements.txt
```

### 3. Running the Script

1.  Make sure the `1.1.6 (final cleanup)` directory is on your desktop, as the script is hardcoded to look for it there.
2.  Navigate to the `code_pusher` directory in your terminal.
3.  Run the script:

    ```bash
    python3 deploy.py
    ```

4.  **Follow the Prompts:** The script will ask for the following information:
    *   **Remote Server IP Address:** The IP of the Ubuntu server you want to deploy to.
    *   **Username:** Your username on the remote server.
    *   **Password:** Your password on the remote server. It will not be visible as you type.
    *   **Path of OLD Application Directory:** The full, absolute path to the old application's code that you want to delete (e.g., `/home/server/old_project`).
    *   **Name of the OLD systemd Service:** The name of the service file for the old application (e.g., `old_app.service`).

The script will then execute all the deployment steps, printing its progress along the way. If any step fails, it will report the error and continue where possible.
