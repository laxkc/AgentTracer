"""Debug script to test Phase 2 ingestion and see validation errors"""
import httpx
import json
from datetime import datetime, timezone
from uuid import uuid4

# Build IDs first
step_id = str(uuid4())

# Build a simple Phase 2 payload
payload = {
    "run_id": str(uuid4()),
    "agent_id": "test_agent",
    "agent_version": "2.0.0",
    "environment": "production",
    "status": "success",
    "started_at": datetime.now(timezone.utc).isoformat(),
    "ended_at": datetime.now(timezone.utc).isoformat(),
    "steps": [
        {
            "step_id": step_id,
            "seq": 0,
            "step_type": "plan",
            "name": "test_step",
            "latency_ms": 100,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "ended_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {}
        }
    ],
    "decisions": [
        {
            "decision_id": str(uuid4()),
            "step_id": step_id,  # Reference the step
            "decision_type": "tool_selection",
            "selected": "api",
            "reason_code": "fresh_data_required",
            "confidence": 0.85,
            "metadata": {}
        }
    ],
    "quality_signals": [
        {
            "signal_id": str(uuid4()),
            "step_id": step_id,  # Reference the step
            "signal_type": "tool_success",
            "signal_code": "first_attempt",
            "value": True,
            "weight": 1.0,
            "metadata": {}
        }
    ]
}

# Send the request
try:
    response = httpx.post(
        "http://localhost:8000/v1/runs",
        json=payload,
        timeout=10.0
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    if response.status_code == 422:
        print("\n❌ Validation Error Details:")
        print(json.dumps(response.json(), indent=2))
    else:
        print("\n✅ Success!")
except Exception as e:
    print(f"Error: {e}")
