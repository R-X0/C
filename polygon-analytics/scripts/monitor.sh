#!/bin/bash

# Comprehensive monitoring script for Polygon Analytics Platform

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}         POLYGON ANALYTICS PLATFORM - SYSTEM MONITOR          ${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Function to check service status
check_service() {
    local service_name=$1
    local port=$2
    local url=$3
    
    if curl -s -o /dev/null -w "%{http_code}" $url | grep -q "200"; then
        echo -e "${GREEN}✅ $service_name${NC} - Running on port $port"
        return 0
    else
        echo -e "${RED}❌ $service_name${NC} - Not responding on port $port"
        return 1
    fi
}

# System Information
echo -e "${YELLOW}📊 SYSTEM INFORMATION${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Hostname: $(hostname)"
echo "IP Address: $(hostname -I | awk '{print $1}')"
echo "Uptime: $(uptime -p)"
echo "Date: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# CPU and Memory Usage
echo -e "${YELLOW}💻 RESOURCE USAGE${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "CPU Usage: $(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1"%"}')"
echo "Memory Usage: $(free -h | awk '/^Mem:/ {printf "%s / %s (%.1f%%)", $3, $2, $3/$2 * 100}')"
echo "Disk Usage: $(df -h / | awk 'NR==2 {printf "%s / %s (%s)", $3, $2, $5}')"
echo ""

# Service Status
echo -e "${YELLOW}🔧 SERVICE STATUS${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check FastAPI
check_service "FastAPI Backend" 8000 "http://localhost:8000/"

# Check Streamlit
check_service "Streamlit Frontend" 8501 "http://localhost:8501/"

# Check PostgreSQL
if docker exec polygon-analytics-postgres-1 pg_isready -U postgres > /dev/null 2>&1; then
    echo -e "${GREEN}✅ PostgreSQL${NC} - Database is ready"
    # Get database size
    DB_SIZE=$(docker exec polygon-analytics-postgres-1 psql -U postgres -d polygon_analytics -t -c "SELECT pg_size_pretty(pg_database_size('polygon_analytics'));" 2>/dev/null | xargs)
    echo "   └─ Database Size: ${DB_SIZE:-N/A}"
else
    echo -e "${RED}❌ PostgreSQL${NC} - Database not responding"
fi

# Check Redis
if docker exec polygon-analytics-redis-1 redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Redis${NC} - Cache is ready"
    # Get Redis memory usage
    REDIS_MEM=$(docker exec polygon-analytics-redis-1 redis-cli INFO memory | grep used_memory_human | cut -d: -f2 | tr -d '\r')
    echo "   └─ Memory Usage: ${REDIS_MEM:-N/A}"
else
    echo -e "${RED}❌ Redis${NC} - Cache not responding"
fi

echo ""

# Docker Container Status
echo -e "${YELLOW}🐳 DOCKER CONTAINERS${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep polygon-analytics || echo "No containers running"
echo ""

# Process Status
echo -e "${YELLOW}📝 APPLICATION PROCESSES${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check for uvicorn process
if pgrep -f "uvicorn app.main:app" > /dev/null; then
    PID=$(pgrep -f "uvicorn app.main:app" | head -1)
    MEM=$(ps -o %mem= -p $PID | xargs)
    CPU=$(ps -o %cpu= -p $PID | xargs)
    echo -e "${GREEN}✅ Uvicorn${NC} (PID: $PID) - CPU: ${CPU}% | Memory: ${MEM}%"
else
    echo -e "${RED}❌ Uvicorn${NC} - Not running"
fi

# Check for streamlit process
if pgrep -f "streamlit run" > /dev/null; then
    PID=$(pgrep -f "streamlit run" | head -1)
    MEM=$(ps -o %mem= -p $PID | xargs)
    CPU=$(ps -o %cpu= -p $PID | xargs)
    echo -e "${GREEN}✅ Streamlit${NC} (PID: $PID) - CPU: ${CPU}% | Memory: ${MEM}%"
else
    echo -e "${RED}❌ Streamlit${NC} - Not running"
fi

echo ""

# Recent Logs
echo -e "${YELLOW}📋 RECENT LOG ENTRIES${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -f api.log ]; then
    echo "FastAPI (last 5 lines):"
    tail -5 api.log | sed 's/^/  /'
fi

if [ -f streamlit.log ]; then
    echo "Streamlit (last 5 lines):"
    tail -5 streamlit.log | sed 's/^/  /'
fi

echo ""

# Data Statistics
echo -e "${YELLOW}📈 DATA STATISTICS${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Try to get tick data count from database
if docker exec polygon-analytics-postgres-1 pg_isready -U postgres > /dev/null 2>&1; then
    TICK_COUNT=$(docker exec polygon-analytics-postgres-1 psql -U postgres -d polygon_analytics -t -c "SELECT COUNT(*) FROM tick_data;" 2>/dev/null | xargs)
    TEMPLATE_COUNT=$(docker exec polygon-analytics-postgres-1 psql -U postgres -d polygon_analytics -t -c "SELECT COUNT(*) FROM analytics_templates;" 2>/dev/null | xargs)
    
    echo "Total Tick Records: ${TICK_COUNT:-0}"
    echo "Saved Templates: ${TEMPLATE_COUNT:-0}"
    
    # Get symbols with data
    echo "Symbols with data:"
    docker exec polygon-analytics-postgres-1 psql -U postgres -d polygon_analytics -t -c "SELECT symbol, COUNT(*) as count FROM tick_data GROUP BY symbol ORDER BY count DESC LIMIT 5;" 2>/dev/null | sed 's/^/  /'
fi

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "Monitor completed at $(date '+%Y-%m-%d %H:%M:%S')"