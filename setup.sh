#!/bin/bash
set -e

# Update package lists
echo "Updating package lists..."
apt-get update

# Install required packages
echo "Installing required packages (wget, unzip, curl, jq, and libraries needed for Chrome & ChromeDriver)..."
apt-get install -y wget unzip curl jq libnss3 libgconf-2-dev libx11-xcb1

echo "Installation of required packages complete."