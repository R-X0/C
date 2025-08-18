#!/bin/bash

# Maintenance script for Polygon Analytics Platform

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

DB_NAME="polygon_analytics"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}      POLYGON ANALYTICS - MAINTENANCE TASKS           ${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Function to display menu
show_menu() {
    echo "Select a maintenance task:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "1) Clean old tick data (>30 days)"
    echo "2) Optimize database (VACUUM and ANALYZE)"
    echo "3) Clear Redis cache"
    echo "4) Clean old logs"
    echo "5) Update Python dependencies"
    echo "6) Database statistics report"
    echo "7) Export all templates"
    echo "8) Import templates from file"
    echo "9) Full system cleanup"
    echo "0) Exit"
    echo ""
    echo -n "Enter selection: "
}

# Function to clean old tick data
clean_old_data() {
    echo -e "${YELLOW}Cleaning tick data older than 30 days...${NC}"
    
    # Get count before deletion
    COUNT=$(docker exec polygon-analytics-postgres-1 psql -U postgres -d $DB_NAME -t -c \
        "SELECT COUNT(*) FROM tick_data WHERE created_at < NOW() - INTERVAL '30 days';")
    
    if [ "$COUNT" -gt 0 ]; then
        echo "Found $COUNT records to delete"
        echo -n "Proceed with deletion? (yes/no): "
        read confirm
        
        if [ "$confirm" = "yes" ]; then
            docker exec polygon-analytics-postgres-1 psql -U postgres -d $DB_NAME -c \
                "DELETE FROM tick_data WHERE created_at < NOW() - INTERVAL '30 days';"
            echo -e "${GREEN}✓ Deleted $COUNT old records${NC}"
        else
            echo "Deletion cancelled"
        fi
    else
        echo "No old records found"
    fi
}

# Function to optimize database
optimize_database() {
    echo -e "${YELLOW}Optimizing database...${NC}"
    
    # Run VACUUM to reclaim space
    docker exec polygon-analytics-postgres-1 psql -U postgres -d $DB_NAME -c "VACUUM ANALYZE;"
    
    # Reindex tables
    docker exec polygon-analytics-postgres-1 psql -U postgres -d $DB_NAME -c "REINDEX DATABASE $DB_NAME;"
    
    echo -e "${GREEN}✓ Database optimized${NC}"
}

# Function to clear Redis cache
clear_redis() {
    echo -e "${YELLOW}Clearing Redis cache...${NC}"
    docker exec polygon-analytics-redis-1 redis-cli FLUSHALL
    echo -e "${GREEN}✓ Redis cache cleared${NC}"
}

# Function to clean old logs
clean_logs() {
    echo -e "${YELLOW}Cleaning old log files...${NC}"
    
    # Clean logs older than 7 days
    find . -name "*.log" -type f -mtime +7 -delete
    
    # Truncate current logs if they're too large (>100MB)
    for log in api.log streamlit.log; do
        if [ -f $log ]; then
            SIZE=$(stat -f%z "$log" 2>/dev/null || stat -c%s "$log" 2>/dev/null)
            if [ "$SIZE" -gt 104857600 ]; then
                echo "Truncating $log ($(($SIZE / 1048576))MB)..."
                tail -n 10000 $log > $log.tmp && mv $log.tmp $log
            fi
        fi
    done
    
    echo -e "${GREEN}✓ Logs cleaned${NC}"
}

# Function to update dependencies
update_deps() {
    echo -e "${YELLOW}Updating Python dependencies...${NC}"
    
    if [ -f venv/bin/activate ]; then
        source venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt --upgrade
        echo -e "${GREEN}✓ Dependencies updated${NC}"
    else
        echo -e "${RED}Virtual environment not found${NC}"
    fi
}

# Function to show database statistics
db_stats() {
    echo -e "${YELLOW}Database Statistics${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    docker exec polygon-analytics-postgres-1 psql -U postgres -d $DB_NAME << EOF
    SELECT 'Database Size' as metric, pg_size_pretty(pg_database_size('$DB_NAME')) as value
    UNION ALL
    SELECT 'Tick Data Records', COUNT(*)::text FROM tick_data
    UNION ALL
    SELECT 'Unique Symbols', COUNT(DISTINCT symbol)::text FROM tick_data
    UNION ALL
    SELECT 'Saved Templates', COUNT(*)::text FROM analytics_templates
    UNION ALL
    SELECT 'Query History', COUNT(*)::text FROM query_history
    UNION ALL
    SELECT 'Oldest Data', MIN(timestamp)::text FROM tick_data
    UNION ALL
    SELECT 'Newest Data', MAX(timestamp)::text FROM tick_data;
    
    \echo ''
    \echo 'Table Sizes:'
    SELECT 
        schemaname,
        tablename,
        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
    FROM pg_tables 
    WHERE schemaname = 'public'
    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
EOF
}

# Function to export templates
export_templates() {
    echo -e "${YELLOW}Exporting all templates...${NC}"
    
    EXPORT_FILE="templates_export_$(date +%Y%m%d_%H%M%S).json"
    
    docker exec polygon-analytics-postgres-1 psql -U postgres -d $DB_NAME -t -A -c \
        "SELECT json_agg(row_to_json(t)) FROM analytics_templates t;" > $EXPORT_FILE
    
    if [ -s $EXPORT_FILE ]; then
        echo -e "${GREEN}✓ Templates exported to $EXPORT_FILE${NC}"
    else
        echo -e "${RED}No templates to export${NC}"
        rm -f $EXPORT_FILE
    fi
}

# Function to import templates
import_templates() {
    echo "Available template files:"
    ls -1 templates_*.json 2>/dev/null
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}No template files found${NC}"
        return
    fi
    
    echo -n "Enter filename to import: "
    read filename
    
    if [ ! -f "$filename" ]; then
        echo -e "${RED}File not found${NC}"
        return
    fi
    
    # Import logic would go here
    echo -e "${YELLOW}Import functionality requires API endpoint${NC}"
}

# Function for full cleanup
full_cleanup() {
    echo -e "${RED}⚠️  Full System Cleanup${NC}"
    echo "This will:"
    echo "- Clean old tick data"
    echo "- Optimize database"
    echo "- Clear Redis cache"
    echo "- Clean logs"
    echo ""
    echo -n "Are you sure? (yes/no): "
    read confirm
    
    if [ "$confirm" = "yes" ]; then
        clean_old_data
        optimize_database
        clear_redis
        clean_logs
        echo -e "${GREEN}✓ Full cleanup completed${NC}"
    else
        echo "Cleanup cancelled"
    fi
}

# Main menu loop
while true; do
    show_menu
    read choice
    
    case $choice in
        1) clean_old_data ;;
        2) optimize_database ;;
        3) clear_redis ;;
        4) clean_logs ;;
        5) update_deps ;;
        6) db_stats ;;
        7) export_templates ;;
        8) import_templates ;;
        9) full_cleanup ;;
        0) echo "Exiting..."; exit 0 ;;
        *) echo -e "${RED}Invalid selection${NC}" ;;
    esac
    
    echo ""
    echo "Press Enter to continue..."
    read
    clear
done