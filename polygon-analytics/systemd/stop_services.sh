#!/bin/bash

# Service stop script for systemd

LOG_DIR="/home/ubuntu/polygon-analytics/logs"

# Function to log with timestamp
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> $LOG_DIR/startup.log
}

log_message "Stopping Polygon Analytics Platform services..."

# Stop FastAPI
if [ -f /home/ubuntu/polygon-analytics/api.pid ]; then
    PID=$(cat /home/ubuntu/polygon-analytics/api.pid)
    if kill -0 $PID 2>/dev/null; then
        kill $PID
        log_message "Stopped FastAPI (PID: $PID)"
    fi
    rm -f /home/ubuntu/polygon-analytics/api.pid
fi

# Stop Streamlit
if [ -f /home/ubuntu/polygon-analytics/streamlit.pid ]; then
    PID=$(cat /home/ubuntu/polygon-analytics/streamlit.pid)
    if kill -0 $PID 2>/dev/null; then
        kill $PID
        log_message "Stopped Streamlit (PID: $PID)"
    fi
    rm -f /home/ubuntu/polygon-analytics/streamlit.pid
fi

# Give processes time to shutdown gracefully
sleep 2

# Force kill if still running
pkill -f "uvicorn app.main:app" 2>/dev/null
pkill -f "streamlit run frontend/app.py" 2>/dev/null

log_message "All services stopped"
exit 0