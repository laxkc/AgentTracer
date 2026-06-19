#!/bin/bash

# Restart script for localGPT servers with tracer enabled

echo "=========================================="
echo "🔄 Restarting localGPT servers"
echo "=========================================="

# Kill existing servers
echo "🛑 Stopping existing servers..."
lsof -ti:8100 | xargs kill -9 2>/dev/null && echo "  ✓ Backend server (8100) stopped"
lsof -ti:8101 | xargs kill -9 2>/dev/null && echo "  ✓ RAG API server (8101) stopped"

sleep 2

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Activate virtual environment
source venv/bin/activate

echo ""
echo "=========================================="
echo "🚀 Starting Backend Server (port 8100)"
echo "=========================================="
python backend/server.py > /tmp/localgpt-backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# Wait a moment and check if backend started
sleep 2
if ps -p $BACKEND_PID > /dev/null; then
    echo "✅ Backend server started successfully"
    # Show tracer status
    grep -E "AgentTracer|Tracer Status" /tmp/localgpt-backend.log
else
    echo "❌ Backend server failed to start"
    cat /tmp/localgpt-backend.log
    exit 1
fi

echo ""
echo "=========================================="
echo "🚀 Starting RAG API Server (port 8101)"
echo "=========================================="
python -m rag_system.api_server > /tmp/localgpt-rag.log 2>&1 &
RAG_PID=$!
echo "RAG API PID: $RAG_PID"

# Wait for RAG to initialize (it takes longer)
echo "⏳ Waiting for RAG agent to initialize..."
sleep 5

if ps -p $RAG_PID > /dev/null; then
    echo "✅ RAG API server started successfully"
    # Show tracer status
    grep -E "AgentTracer|Tracer Status" /tmp/localgpt-rag.log
else
    echo "❌ RAG API server failed to start"
    cat /tmp/localgpt-rag.log
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ All servers started successfully"
echo "=========================================="
echo ""
echo "📊 Server Status:"
echo "  Backend:  http://localhost:8100  (PID: $BACKEND_PID)"
echo "  RAG API:  http://localhost:8101  (PID: $RAG_PID)"
echo ""
echo "📝 Log files:"
echo "  Backend:  tail -f /tmp/localgpt-backend.log"
echo "  RAG API:  tail -f /tmp/localgpt-rag.log"
echo ""
echo "🔍 To test tracer:"
echo "  curl -s \"http://localhost:8001/v1/runs?limit=5\" | jq '.[] | {agent_id, status, started_at}'"
echo ""
