#!/bin/bash
# Agent Observability Platform - UI Startup Script

set -e

echo "========================================="
echo "Agent Observability Platform - UI"
echo "========================================="
echo ""

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
    echo "✅ Dependencies installed"
    echo ""
fi

# Check if backend APIs are running
echo "🔍 Checking backend APIs..."

if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Ingest API is running (port 8000)"
else
    echo "⚠️  Ingest API not detected on port 8000"
    echo "   Please start with: python -m backend.ingest_api"
fi

if curl -s http://localhost:8001/health > /dev/null 2>&1; then
    echo "✅ Query API is running (port 8001)"
else
    echo "⚠️  Query API not detected on port 8001"
    echo "   Please start with: python -m backend.query_api"
fi

echo ""
echo "🚀 Starting development server..."
echo "   UI will be available at: http://localhost:3000"
echo ""
echo "========================================="

# Start development server
npm run dev
