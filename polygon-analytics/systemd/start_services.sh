#!/bin/bash

# Service startup script for systemd
# This runs with proper environment setup

set -e

LOG_DIR="/home/ubuntu/polygon-analytics/logs"
mkdir -p $LOG_DIR

# Function to log with timestamp
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> $LOG_DIR/startup.log
}

log_message "Starting Polygon Analytics Platform services..."

# Activate virtual environment
source /home/ubuntu/polygon-analytics/venv/bin/activate

# Start FastAPI in background
log_message "Starting FastAPI backend..."
nohup uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 2 \
    --log-level info \
    > $LOG_DIR/api.log 2>&1 &

echo $! > /home/ubuntu/polygon-analytics/api.pid
log_message "FastAPI started with PID $(cat /home/ubuntu/polygon-analytics/api.pid)"

# Wait a moment for API to initialize
sleep 5

# Start Streamlit in background
log_message "Starting Streamlit frontend..."
nohup streamlit run frontend/app.py \
    --server.port 8501 \
    --server.address 0.0.0.0 \
    --server.headless true \
    --browser.serverAddress localhost \
    --browser.gatherUsageStats false \
    > $LOG_DIR/streamlit.log 2>&1 &

echo $! > /home/ubuntu/polygon-analytics/streamlit.pid
log_message "Streamlit started with PID $(cat /home/ubuntu/polygon-analytics/streamlit.pid)"

# Verify services are running
sleep 5

if kill -0 $(cat /home/ubuntu/polygon-analytics/api.pid) 2>/dev/null; then
    log_message "FastAPI is running"
else
    log_message "ERROR: FastAPI failed to start"
    exit 1
fi

if kill -0 $(cat /home/ubuntu/polygon-analytics/streamlit.pid) 2>/dev/null; then
    log_message "Streamlit is running"
else
    log_message "ERROR: Streamlit failed to start"
    exit 1
fi

log_message "All services started successfully"
exit 0