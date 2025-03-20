# Headscale Self-Registration Web Application

A simple web application that allows users to self-register their nodes to a Headscale server without requiring direct access to server commands.

> ### ⚠️ Important Notes: 
>
> This application has no authentication. If an attacker knows that there is a Headscale coordinator on your server and knows the existence of this website, then he can easily infiltrate your Tailnet. 
>
> #### USE AT YOUR *OWN* RISK!

## Introduction

This project helps users who want to connect to your Headscale server to self-complete the verification process. It provides a web interface where users can input their Node ID and select or create a user namespace in Headscale.

![image-20250320154223214](https://geelao-oss.oss-cn-hangzhou.aliyuncs.com/db/202503201542305.png?x-oss-process=style/jpeg)

### Requirements

- Must be deployed on the same server as your Headscale installation

- Requires root access to execute Headscale commands

- `default` user exists in Headscale

  ```bash
  headscale users create default
  ```

  

- Python 3.6+

## Usage Guide

### For End Users

1. On your client device, run:

   ```
   tailscale login --login-server https://your-headscale-server
   ```

2. You will receive a Node ID (also called a machine key)

3. Open the self-registration website URL provided by the Headscale administrator

4. Enter your Node ID in the form field

5. Select an existing user namespace or create a new one

6. Click "Register" button

7. Check the result:

   - Success message indicates your device is now connected to the Tailnet
   - If you see an error message, contact the Headscale server administrator for assistance

## Installation

### Setup

1. Clone this repository:

   ```bash
   git clone https://github.com/yourusername/headscale-self-register.git
   cd headscale-self-register
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. *(Optional)* Periodically update user list:

   ```sh
   # add this to your crontab
   15 */2 * * * headscale users list -ojson > /root/headscale_users.json
   ```

### Direct Startup

You can start the application directly using Waitress:

```bash
python serve.py
```

By default, the server will listen on `0.0.0.0:5000`. You can customize the host, port, and thread count using environment variables:

```bash
export HOST=0.0.0.0  # Listen on all interfaces
export PORT=5000     # Port number
export THREADS=4     # Number of worker threads
python waitress_server.py
```

### Process Management

#### Using PM2

[PM2](https://pm2.keymetrics.io/) is a process manager for Node.js applications, but it can also manage Python applications.

1. Install PM2 if you haven't already:

   ```bash
   npm install -g pm2
   ```

2. Start the application with PM2:

   ```bash
   pm2 start serve.py --name headscale-self-reg --interpreter=/path/to/python
   ```

   For example, if using Miniconda:

   ```bash
   pm2 start serve.py --name headscale-self-reg --interpreter=/opt/miniconda3/bin/python
   ```

3. Set PM2 to start on boot:

   ```bash
   pm2 save
   pm2 startup
   ```

#### Using Systemd

1. Create a systemd service file:

   ```bash
   sudo nano /etc/systemd/system/headscale-self-reg.service
   ```

2. Add the following content (adjust paths as needed):

   ```ini
   [Unit]
   Description=Headscale Self-Registration Web Application
   After=network.target
   
   [Service]
   User=your_username
   Group=your_group
   WorkingDirectory=/path/to/headscale-self-register
   Environment="PATH=/path/to/your/python/venv/bin"
   ExecStart=/path/to/your/python/venv/bin/python serve.py
   Restart=always
   RestartSec=5
   StartLimitIntervalSec=0
   
   # Environment variables (optional)
   Environment="HOST=0.0.0.0"
   Environment="PORT=8080"
   Environment="THREADS=4"
   
   [Install]
   WantedBy=multi-user.target
   ```

3. Enable and start the service:

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable headscale-self-reg
   sudo systemctl start headscale-self-reg
   ```

4. Check the service status:

   ```bash
   sudo systemctl status headscale-self-reg
   ```

## Security Considerations

This application runs commands with sudo privileges and has no built-in authentication. Consider implementing additional security measures:

1. Put the application behind a reverse proxy (like Nginx) with basic authentication
2. Use firewall rules to limit access to the registration page
3. Consider deploying on a private network rather than exposing it to the internet
4. Monitor logs regularly for unauthorized access attempts

## Logs

Application logs are stored in the `logs` directory:

- `logs/headscale_app.log` - Application logs
- `logs/waitress.log` - Server logs
