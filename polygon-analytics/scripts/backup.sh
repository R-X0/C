#!/bin/bash

# Backup script for Polygon Analytics Platform

# Configuration
BACKUP_DIR="/home/ubuntu/backups"
DB_NAME="polygon_analytics"
RETENTION_DAYS=7
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}Starting backup process...${NC}"

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Function to handle errors
handle_error() {
    echo -e "${RED}Error: $1${NC}"
    exit 1
}

# 1. Backup PostgreSQL database
echo "Backing up PostgreSQL database..."
docker exec polygon-analytics-postgres-1 pg_dump -U postgres $DB_NAME > $BACKUP_DIR/db_backup_$TIMESTAMP.sql || handle_error "Failed to backup database"

# Compress the database backup
gzip $BACKUP_DIR/db_backup_$TIMESTAMP.sql
echo -e "${GREEN}✓ Database backed up to: db_backup_$TIMESTAMP.sql.gz${NC}"

# 2. Backup application configuration
echo "Backing up application configuration..."
tar -czf $BACKUP_DIR/config_backup_$TIMESTAMP.tar.gz \
    .env \
    docker-compose.yml \
    2>/dev/null || echo "Warning: Some config files may be missing"

echo -e "${GREEN}✓ Configuration backed up to: config_backup_$TIMESTAMP.tar.gz${NC}"

# 3. Backup saved templates (export from database)
echo "Exporting analytics templates..."
docker exec polygon-analytics-postgres-1 psql -U postgres -d $DB_NAME -c "\
    COPY (SELECT * FROM analytics_templates) TO STDOUT WITH CSV HEADER;" \
    > $BACKUP_DIR/templates_backup_$TIMESTAMP.csv 2>/dev/null

if [ -s $BACKUP_DIR/templates_backup_$TIMESTAMP.csv ]; then
    gzip $BACKUP_DIR/templates_backup_$TIMESTAMP.csv
    echo -e "${GREEN}✓ Templates backed up to: templates_backup_$TIMESTAMP.csv.gz${NC}"
else
    rm -f $BACKUP_DIR/templates_backup_$TIMESTAMP.csv
    echo "No templates to backup"
fi

# 4. Create backup summary
cat > $BACKUP_DIR/backup_$TIMESTAMP.info << EOF
Backup Summary
==============
Date: $(date)
Database: $DB_NAME
Files:
- db_backup_$TIMESTAMP.sql.gz
- config_backup_$TIMESTAMP.tar.gz
- templates_backup_$TIMESTAMP.csv.gz

Database Statistics:
$(docker exec polygon-analytics-postgres-1 psql -U postgres -d $DB_NAME -t -c "SELECT 'Tick Records: ' || COUNT(*) FROM tick_data;")
$(docker exec polygon-analytics-postgres-1 psql -U postgres -d $DB_NAME -t -c "SELECT 'Templates: ' || COUNT(*) FROM analytics_templates;")
$(docker exec polygon-analytics-postgres-1 psql -U postgres -d $DB_NAME -t -c "SELECT 'Query History: ' || COUNT(*) FROM query_history;")
EOF

echo -e "${GREEN}✓ Backup summary saved${NC}"

# 5. Clean up old backups
echo "Cleaning up old backups (older than $RETENTION_DAYS days)..."
find $BACKUP_DIR -type f -name "*.gz" -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -type f -name "*.info" -mtime +$RETENTION_DAYS -delete

# 6. Calculate backup size
BACKUP_SIZE=$(du -sh $BACKUP_DIR | cut -f1)
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}Backup completed successfully!${NC}"
echo "Location: $BACKUP_DIR"
echo "Total backup size: $BACKUP_SIZE"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"