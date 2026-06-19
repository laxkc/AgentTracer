# LocalGPT × AgentTracer integration

This example shows how to add **AgentTracer** tracing to
[**localGPT**](https://github.com/PromtEngineer/localGPT) (by PromtEngineer), a
private document-intelligence / RAG platform.

To keep this repository lean, the upstream localGPT source is **not** vendored
here. This directory contains only the files modified to emit AgentTracer
telemetry — the ones you drop in on top of a localGPT checkout.

## Files

| File | Replaces in upstream localGPT | What changed |
| ---- | ----------------------------- | ------------ |
| `backend/server.py` | `backend/server.py` | Instruments the backend API with AgentTracer spans |
| `rag_system/api_server.py` | `rag_system/api_server.py` | Traces the RAG retrieval/generation pipeline |
| `restart-servers.sh` | `restart-servers.sh` | Convenience restart script for the traced services |

## Usage

```bash
# 1. Clone upstream localGPT
git clone https://github.com/PromtEngineer/localGPT.git
cd localGPT

# 2. Overlay the AgentTracer-instrumented files from this directory
cp /path/to/examples/localgpt-integration/backend/server.py        backend/server.py
cp /path/to/examples/localgpt-integration/rag_system/api_server.py rag_system/api_server.py
cp /path/to/examples/localgpt-integration/restart-servers.sh       restart-servers.sh

# 3. Install the AgentTracer SDK and run localGPT per its own README
pip install -e /path/to/this/repo
./restart-servers.sh
```

## Attribution

localGPT is © its authors and distributed under the Apache License 2.0. See the
upstream repository for its full license and documentation. Only the
modifications in this directory are part of this project.
