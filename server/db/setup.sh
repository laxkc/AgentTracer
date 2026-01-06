#!/bin/bash
# AgentTracer Platform - Database Setup Script
#
# This script initializes the PostgreSQL database and creates the schema.
# Usage: ./db/setup.sh

set -e

# Configuration
DB_NAME="agent_observability"
DB_USER="postgres"
DB_PASSWORD="postgres"
DB_HOST="localhost"
DB_PORT="5432"

echo "========================================="
echo "AgentTracer - Database Setup"
echo "========================================="
echo ""

# Check if PostgreSQL is running
echo "🔍 Checking PostgreSQL connection..."
if ! psql -h $DB_HOST -p $DB_PORT -U $DB_USER -lqt | cut -d \| -f 1 | grep -qw template1; then
    echo "❌ PostgreSQL is not running or not accessible"
    echo "   Please start PostgreSQL first:"
    echo "   - Docker: docker-compose up -d postgres"
    echo "   - Local: brew services start postgresql (macOS)"
    exit 1
fi
echo "✅ PostgreSQL is running"
echo ""

# Create database if it doesn't exist
echo "🗄️  Creating database '$DB_NAME'..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -tc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" | grep -q 1 || \
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -c "CREATE DATABASE $DB_NAME"
echo "✅ Database ready"
echo ""

# Apply schema
echo "📋 Applying database schema..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME < "$(dirname "$0")/schema.sql"
echo "✅ Schema applied"
echo ""

# Verify tables
echo "🔍 Verifying tables..."
TABLE_COUNT=$(psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'")
if [ "$TABLE_COUNT" -ge 3 ]; then
    echo "✅ Found $TABLE_COUNT tables"
    psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "\dt"
else
    echo "❌ Expected at least 3 tables, found $TABLE_COUNT"
    exit 1
fi
echo ""

# Apply seed data (optional)
if [ -f "$(dirname "$0")/seed.sql" ]; then
    echo "🌱 Applying seed data..."
    psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME < "$(dirname "$0")/seed.sql"
    echo "✅ Seed data applied"
    echo ""
fi

echo "========================================="
echo "✅ Database setup complete!"
echo "========================================="
echo ""
echo "Connection string:"
echo "  postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME"
echo ""
echo "Next steps:"
echo "  1. Start Ingest API: python -m backend.ingest_api"
echo "  2. Start Query API: python -m backend.query_api"
echo "  3. Run example: python examples/customer_support_agent.py"
echo ""
