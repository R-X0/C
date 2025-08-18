#!/bin/bash

# Restore script for Polygon Analytics Platform

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

BACKUP_DIR="/home/ubuntu/backups"
DB_NAME="polygon_analytics"

echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}        POLYGON ANALYTICS - DATABASE RESTORE          ${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check if backup directory exists
if [ ! -d "$BACKUP_DIR" ]; then
    echo -e "${RED}Error: Backup directory not found at $BACKUP_DIR${NC}"
    exit 1
fi

# List available backups
echo "Available backups:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ls -lh $BACKUP_DIR/*.sql.gz 2>/dev/null | awk '{print NR". "$9" ("$5")"}'

if [ $? -ne 0 ]; then
    echo -e "${RED}No backups found in $BACKUP_DIR${NC}"
    exit 1
fi

echo ""
echo -n "Enter the number of the backup to restore (or 'q' to quit): "
read selection

if [ "$selection" = "q" ]; then
    echo "Restore cancelled."
    exit 0
fi

# Get the selected backup file
BACKUP_FILE=$(ls -1 $BACKUP_DIR/*.sql.gz 2>/dev/null | sed -n "${selection}p")

if [ -z "$BACKUP_FILE" ]; then
    echo -e "${RED}Invalid selection${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}Selected backup: $(basename $BACKUP_FILE)${NC}"
echo ""
echo -e "${RED}⚠️  WARNING: This will replace all current data!${NC}"
echo -n "Are you sure you want to restore this backup? (yes/no): "
read confirm

if [ "$confirm" != "yes" ]; then
    echo "Restore cancelled."
    exit 0
fi

echo ""
echo "Starting restore process..."

# 1. Stop application services
echo "Stopping application services..."
if [ -f api.pid ]; then
    kill $(cat api.pid) 2>/dev/null
fi
if [ -f streamlit.pid ]; then
    kill $(cat streamlit.pid) 2>/dev/null
fi

# 2. Create temporary uncompressed backup
echo "Preparing backup file..."
TEMP_SQL="/tmp/restore_$(date +%s).sql"
gunzip -c $BACKUP_FILE > $TEMP_SQL

# 3. Drop and recreate database
echo "Recreating database..."
docker exec polygon-analytics-postgres-1 psql -U postgres -c "DROP DATABASE IF EXISTS $DB_NAME;"
docker exec polygon-analytics-postgres-1 psql -U postgres -c "CREATE DATABASE $DB_NAME;"

# 4. Restore database
echo "Restoring database..."
docker exec -i polygon-analytics-postgres-1 psql -U postgres -d $DB_NAME < $TEMP_SQL

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Database restored successfully${NC}"
else
    echo -e "${RED}✗ Database restore failed${NC}"
    rm -f $TEMP_SQL
    exit 1
fi

# 5. Clean up temporary file
rm -f $TEMP_SQL

# 6. Verify restore
echo ""
echo "Verifying restore..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

docker exec polygon-analytics-postgres-1 psql -U postgres -d $DB_NAME -c "\
    SELECT 'Tick Records: ' || COUNT(*) FROM tick_data \
    UNION ALL \
    SELECT 'Templates: ' || COUNT(*) FROM analytics_templates \
    UNION ALL \
    SELECT 'Query History: ' || COUNT(*) FROM query_history;"

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}Restore completed successfully!${NC}"
echo ""
echo "Next steps:"
echo "1. Restart the application: ./start.sh"
echo "2. Verify functionality at http://localhost:8501"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"