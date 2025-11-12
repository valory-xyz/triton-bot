#!/bin/bash

USER_NAME=$(whoami)
REPO_PATH=$(pwd)
POETRY_PATH=$(which poetry)
INPUT_FILE="triton.service.template"
OUTPUT_FILE="triton.service"

# Install dependencies
$POETRY_PATH install

# Create triton.service
sed -e "s/{user}/$USER_NAME/g" \
    -e "s|{repo_path}|$REPO_PATH|g" \
    -e "s|{poetry_path}|$POETRY_PATH|g" \
    "$INPUT_FILE" > "$OUTPUT_FILE"

# Stop service if it is running
if systemctl is-active --quiet triton.service; then
    SERVICE_RUNNING=true;
    sudo systemctl stop triton.service;
else
    SERVICE_RUNNING=false;
fi;

# Copy new triton.service
sudo cp triton.service /etc/systemd/system/triton.service;

# Reload service if it was running
sudo systemctl daemon-reload;
if [ "$SERVICE_RUNNING" = "true" ]; then
    sudo systemctl start triton.service;
fi