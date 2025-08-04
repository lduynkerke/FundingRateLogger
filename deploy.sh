#!/bin/bash

# FundingRateLogger Deployment Script
# This script sets up the FundingRateLogger application on a Linux server

set -e  # Exit immediately if a command exits with a non-zero status

echo "===== FundingRateLogger Deployment Script ====="
echo "Starting deployment at $(date)"

# Check if Python 3.8+ is installed
python_version=$(python3 --version 2>&1 | awk '{print $2}')
if [[ -z "$python_version" ]]; then
    echo "ERROR: Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

major=$(echo $python_version | cut -d. -f1)
minor=$(echo $python_version | cut -d. -f2)

if [[ $major -lt 3 || ($major -eq 3 && $minor -lt 8) ]]; then
    echo "ERROR: Python version must be 3.8 or higher. Current version: $python_version"
    exit 1
fi

echo "Python version $python_version detected."

# Create requirements.txt if it doesn't exist
if [[ ! -f "requirements.txt" ]]; then
    echo "Creating requirements.txt file..."
    cat > requirements.txt << EOF
schedule>=1.1.0
requests>=2.28.0
pyyaml>=6.0
httpx>=0.23.0
pytest>=7.0.0  # For running tests
EOF
    echo "requirements.txt created."
fi

# Create virtual environment
echo "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create logs directory if it doesn't exist
if [[ ! -d "logs" ]]; then
    echo "Creating logs directory..."
    mkdir -p logs
fi

# Check if config.yaml exists and has API keys
if [[ ! -f "config.yaml" ]]; then
    echo "ERROR: config.yaml not found. Please create a config.yaml file with your MEXC API credentials."
    exit 1
fi

# Check if API keys are set in config.yaml
api_key=$(grep "api_key:" config.yaml | awk -F'"' '{print $2}')
secret_key=$(grep "secret_key:" config.yaml | awk -F'"' '{print $2}')

if [[ "$api_key" == "your_api_key_here" || "$secret_key" == "your_secret_key_here" ]]; then
    echo "WARNING: Default API keys detected in config.yaml. Please update with your actual MEXC API credentials."
fi

# Create systemd service file
echo "Creating systemd service file..."
sudo tee /etc/systemd/system/fundingratelogger.service > /dev/null << EOF
[Unit]
Description=FundingRateLogger Service
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/venv/bin/python $(pwd)/main.py
Restart=always
RestartSec=10
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=fundingratelogger

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
echo "Reloading systemd..."
sudo systemctl daemon-reload

# Enable and start the service
echo "Enabling and starting FundingRateLogger service..."
sudo systemctl enable fundingratelogger.service
sudo systemctl start fundingratelogger.service

echo "Checking service status..."
sudo systemctl status fundingratelogger.service

echo ""
echo "===== Deployment Complete ====="
echo "FundingRateLogger has been deployed as a systemd service."
echo ""
echo "Useful commands:"
echo "  - Check service status: sudo systemctl status fundingratelogger.service"
echo "  - View logs: sudo journalctl -u fundingratelogger.service"
echo "  - Restart service: sudo systemctl restart fundingratelogger.service"
echo "  - Stop service: sudo systemctl stop fundingratelogger.service"
echo ""
echo "Application logs are stored in the logs directory."