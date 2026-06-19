import json
import http.server
import socketserver
import os
import uuid
from urllib.parse import urlparse
import requests  # 🆕 Import requests for making HTTP calls
import sys
from datetime import datetime
import io
from contextlib import nullcontext

# Add parent directory to path so we can import rag_system modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import RAG system modules for complete metadata
try:
    from rag_system.main import PIPELINE_CONFIGS
    RAG_SYSTEM_AVAILABLE = True
    print("✅ RAG system modules accessible from backend")
except ImportError as e:
    PIPELINE_CONFIGS = {}
    RAG_SYSTEM_AVAILABLE = False
    print(f"⚠️ RAG system modules not available: {e}")

from ollama_client import OllamaClient
from database import db, generate_session_title
import simple_pdf_processor as pdf_module
from simple_pdf_processor import initialize_simple_pdf_processor
from typing import List, Dict, Any
import re

# RAG API base URL (defaults to local RAG API server)
RAG_API_BASE_URL = os.getenv("RAG_API_URL", "http://localhost:8101").rstrip("/")
RAG_API_CHAT_URL = f"{RAG_API_BASE_URL}/chat"
RAG_API_INDEX_URL = f"{RAG_API_BASE_URL}/index"

# --- AgentTracer (optional) ---
def _bool_env(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


def _init_tracer():
    if not _bool_env("TRACER_ENABLED", True):
        print("⚠️ AgentTracer disabled via TRACER_ENABLED=false")
        return None
    try:
        # Add parent directory to path for SDK import
        # backend/server.py -> backend -> localGPT -> examples -> testing
        parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)

        from sdk.agenttrace import AgentTracer

        tracer = AgentTracer(
            agent_id=os.getenv("TRACER_BACKEND_AGENT_ID", "localgpt_backend"),
            agent_version=os.getenv("TRACER_BACKEND_AGENT_VERSION", "2.0"),
            api_url=os.getenv("TRACER_API_URL", "http://localhost:8000"),
            environment=os.getenv("TRACER_ENVIRONMENT", "dev"),
            api_key=os.getenv("TRACER_API_KEY"),
        )
        print(f"✅ AgentTracer initialized for Backend: agent_id=localgpt_backend, api_url=http://localhost:8000")
        return tracer
    except Exception as e:
        print(f"⚠️ AgentTracer SDK initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return None


TRACER = _init_tracer()
print(f"🔍 Backend Tracer Status: {'ENABLED' if TRACER else 'DISABLED'}")


def _run_ctx():
    return TRACER.start_run() if TRACER else nullcontext()


def _step_ctx(run, step_type: str, name: str):
    return run.step(step_type, name) if run else nullcontext()


# 🆕 Reusable TCPServer with address reuse enabled
class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

# Simple multipart parser for Python 3.13+ (replaces cgi.FieldStorage)
def parse_multipart_form(rfile, headers):
    """Parse multipart/form-data without cgi module (Python 3.13+)"""
    content_type = headers.get('Content-Type', '')
    if 'boundary=' not in content_type:
        return {}

    boundary = content_type.split('boundary=')[1].strip()
    if boundary.startswith('"') and boundary.endswith('"'):
        boundary = boundary[1:-1]

    boundary_bytes = f'--{boundary}'.encode()
    content_length = int(headers.get('Content-Length', 0))
    body = rfile.read(content_length)

    parts = body.split(boundary_bytes)
    files = []

    for part in parts[1:-1]:  # Skip first and last (empty)
        if not part.strip():
            continue

        # Split headers and content
        header_end = part.find(b'\r\n\r\n')
        if header_end == -1:
            continue

        headers_bytes = part[:header_end]
        content = part[header_end + 4:]

        # Remove trailing \r\n
        if content.endswith(b'\r\n'):
            content = content[:-2]

        # Parse Content-Disposition header
        headers_str = headers_bytes.decode('utf-8', errors='ignore')
        filename = None
        name = None

        for line in headers_str.split('\r\n'):
            if line.lower().startswith('content-disposition:'):
                parts = line.split(';')
                for p in parts:
                    p = p.strip()
                    if p.startswith('filename='):
                        filename = p.split('=', 1)[1].strip('"')
                    elif p.startswith('name='):
                        name = p.split('=', 1)[1].strip('"')

        if filename and name:
            # Create a file-like object
            class FileItem:
                def __init__(self, filename, content):
                    self.filename = filename
                    self.file = io.BytesIO(content)

            files.append(FileItem(filename, content))

    return {'files': files if len(files) > 1 else (files[0] if files else None)}

class ChatHandler(http.server.BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.ollama_client = OllamaClient()
        super().__init__(*args, **kwargs)
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/health':
            self.send_json_response({
                "status": "ok",
                "ollama_running": self.ollama_client.is_ollama_running(),
                "available_models": self.ollama_client.list_models(),
                "database_stats": db.get_stats()
            })
        elif parsed_path.path == '/sessions':
            self.handle_get_sessions()
        elif parsed_path.path == '/sessions/cleanup':
            self.handle_cleanup_sessions()
        elif parsed_path.path == '/models':
            self.handle_get_models()
        elif parsed_path.path == '/indexes':
            self.handle_get_indexes()
        elif parsed_path.path.startswith('/indexes/') and parsed_path.path.count('/') == 2:
            index_id = parsed_path.path.split('/')[-1]
            self.handle_get_index(index_id)
        elif parsed_path.path.startswith('/sessions/') and parsed_path.path.endswith('/documents'):
            session_id = parsed_path.path.split('/')[-2]
            self.handle_get_session_documents(session_id)
        elif parsed_path.path.startswith('/sessions/') and parsed_path.path.endswith('/indexes'):
            session_id = parsed_path.path.split('/')[-2]
            self.handle_get_session_indexes(session_id)
        elif parsed_path.path.startswith('/sessions/') and parsed_path.path.count('/') == 2:
            session_id = parsed_path.path.split('/')[-1]
            self.handle_get_session(session_id)
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        """Handle POST requests"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/chat':
            self.handle_chat()
        elif parsed_path.path == '/sessions':
            self.handle_create_session()
        elif parsed_path.path == '/indexes':
            self.handle_create_index()
        elif parsed_path.path.startswith('/indexes/') and parsed_path.path.endswith('/upload'):
            index_id = parsed_path.path.split('/')[-2]
            self.handle_index_file_upload(index_id)
        elif parsed_path.path.startswith('/indexes/') and parsed_path.path.endswith('/build'):
            index_id = parsed_path.path.split('/')[-2]
            self.handle_build_index(index_id)
        elif parsed_path.path.startswith('/sessions/') and '/indexes/' in parsed_path.path:
            parts = parsed_path.path.split('/')
            session_id = parts[2]
            index_id = parts[4]
            self.handle_link_index_to_session(session_id, index_id)
        elif parsed_path.path.startswith('/sessions/') and parsed_path.path.endswith('/messages'):
            session_id = parsed_path.path.split('/')[-2]
            self.handle_session_chat(session_id)
        elif parsed_path.path.startswith('/sessions/') and parsed_path.path.endswith('/upload'):
            session_id = parsed_path.path.split('/')[-2]
            self.handle_file_upload(session_id)
        elif parsed_path.path.startswith('/sessions/') and parsed_path.path.endswith('/index'):
            session_id = parsed_path.path.split('/')[-2]
            self.handle_index_documents(session_id)
        elif parsed_path.path.startswith('/sessions/') and parsed_path.path.endswith('/rename'):
            session_id = parsed_path.path.split('/')[-2]
            self.handle_rename_session(session_id)
        else:
            self.send_response(404)
            self.end_headers()

    def do_DELETE(self):
        """Handle DELETE requests"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path.startswith('/sessions/') and parsed_path.path.count('/') == 2:
            session_id = parsed_path.path.split('/')[-1]
            self.handle_delete_session(session_id)
        elif parsed_path.path.startswith('/indexes/') and parsed_path.path.count('/') == 2:
            index_id = parsed_path.path.split('/')[-1]
            self.handle_delete_index(index_id)
        else:
            self.send_response(404)
            self.end_headers()
    
    def handle_chat(self):
        """Handle legacy chat requests (without sessions)"""
        with _run_ctx() as run:
            try:
                with _step_ctx(run, "plan", "parse_request") as step:
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length)
                    data = json.loads(post_data.decode('utf-8'))
                    if run:
                        run.record_quality_signal(
                            signal_type="schema_valid",
                            signal_code="full_match",
                            value=True,
                            step_id=step.step_id,
                        )
                
                message = data.get('message', '')
                model = data.get('model', 'llama3.2:latest')
                conversation_history = data.get('conversation_history', [])
                
                if run:
                    run.record_decision(
                        decision_type="tool_selection",
                        selected="ollama",
                        reason_code="latency_optimization",
                        step_id=step.step_id,
                    )
                
                if not message:
                    if run:
                        run.record_failure(
                            failure_type="orchestration",
                            failure_code="schema_invalid",
                            message="Missing required message field",
                            step_id=step.step_id,
                        )
                    self.send_json_response({
                        "error": "Message is required"
                    }, status_code=400)
                    return
                
                # Check if Ollama is running
                if not self.ollama_client.is_ollama_running():
                    if run:
                        run.record_failure(
                            failure_type="tool",
                            failure_code="ollama_offline",
                            message="Ollama not running",
                            step_id=step.step_id,
                        )
                    self.send_json_response({
                        "error": "Ollama is not running. Please start Ollama first."
                    }, status_code=503)
                    return
                
                # Get response from Ollama
                with _step_ctx(run, "tool", "ollama_chat"):
                    response = self.ollama_client.chat(message, model, conversation_history)
                
                with _step_ctx(run, "respond", "send_response"):
                    self.send_json_response({
                        "response": response,
                        "model": model,
                        "message_count": len(conversation_history) + 1
                    })
                
            except json.JSONDecodeError:
                if run:
                    run.record_quality_signal(
                        signal_type="schema_valid",
                        signal_code="validation_failed",
                        value=True,
                    )
                    run.record_failure(
                        failure_type="orchestration",
                        failure_code="json_decode_error",
                        message="Invalid JSON payload",
                    )
                self.send_json_response({
                    "error": "Invalid JSON"
                }, status_code=400)
            except Exception as e:
                if run:
                    run.record_failure(
                        failure_type="orchestration",
                        failure_code="server_error",
                        message=f"Unhandled error: {type(e).__name__}",
                    )
                self.send_json_response({
                    "error": f"Server error: {str(e)}"
                }, status_code=500)
    
    def handle_get_sessions(self):
        """Get all chat sessions"""
        try:
            sessions = db.get_sessions()
            self.send_json_response({
                "sessions": sessions,
                "total": len(sessions)
            })
        except Exception as e:
            self.send_json_response({
                "error": f"Failed to get sessions: {str(e)}"
            }, status_code=500)
    
    def handle_cleanup_sessions(self):
        """Clean up empty sessions"""
        try:
            cleanup_count = db.cleanup_empty_sessions()
            self.send_json_response({
                "message": f"Cleaned up {cleanup_count} empty sessions",
                "cleanup_count": cleanup_count
            })
        except Exception as e:
            self.send_json_response({
                "error": f"Failed to cleanup sessions: {str(e)}"
            }, status_code=500)
    
    def handle_get_session(self, session_id: str):
        """Get a specific session with its messages"""
        try:
            session = db.get_session(session_id)
            if not session:
                self.send_json_response({
                    "error": "Session not found"
                }, status_code=404)
                return
            
            messages = db.get_messages(session_id)
            
            self.send_json_response({
                "session": session,
                "messages": messages
            })
        except Exception as e:
            self.send_json_response({
                "error": f"Failed to get session: {str(e)}"
            }, status_code=500)
    
    def handle_get_session_documents(self, session_id: str):
        """Return documents and basic info for a session."""
        try:
            session = db.get_session(session_id)
            if not session:
                self.send_json_response({"error": "Session not found"}, status_code=404)
                return

            docs = db.get_documents_for_session(session_id)

            # Extract original filenames from stored paths
            filenames = [os.path.basename(p).split('_', 1)[-1] if '_' in os.path.basename(p) else os.path.basename(p) for p in docs]

            self.send_json_response({
                "session": session,
                "files": filenames,
                "file_count": len(docs)
            })
        except Exception as e:
            self.send_json_response({"error": f"Failed to get documents: {str(e)}"}, status_code=500)
    
    def handle_create_session(self):
        """Create a new chat session"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            title = data.get('title', 'New Chat')
            model = data.get('model', 'llama3.2:latest')
            
            session_id = db.create_session(title, model)
            session = db.get_session(session_id)
            
            self.send_json_response({
                "session": session,
                "session_id": session_id
            }, status_code=201)
            
        except json.JSONDecodeError:
            self.send_json_response({
                "error": "Invalid JSON"
            }, status_code=400)
        except Exception as e:
            self.send_json_response({
                "error": f"Failed to create session: {str(e)}"
            }, status_code=500)
    
    def handle_session_chat(self, session_id: str):
        """
        Handle chat within a specific session.
        Intelligently routes between direct LLM (fast) and RAG pipeline (document-aware).
        """
        with _run_ctx() as run:
            try:
                session = db.get_session(session_id)
                if not session:
                    if run:
                        run.record_failure(
                            failure_type="orchestration",
                            failure_code="session_not_found",
                            message="Session not found",
                        )
                    self.send_json_response({"error": "Session not found"}, status_code=404)
                    return
                
                with _step_ctx(run, "plan", "parse_request") as step:
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length)
                    data = json.loads(post_data.decode('utf-8'))
                    message = data.get('message', '')
                    if run:
                        run.record_quality_signal(
                            signal_type="schema_valid",
                            signal_code="full_match",
                            value=True,
                            step_id=step.step_id,
                        )

                if not message:
                    if run:
                        run.record_failure(
                            failure_type="orchestration",
                            failure_code="schema_invalid",
                            message="Missing required message field",
                            step_id=step.step_id,
                        )
                    self.send_json_response({"error": "Message is required"}, status_code=400)
                    return

                if session['message_count'] == 0:
                    title = generate_session_title(message)
                    db.update_session_title(session_id, title)

                # Add user message to database first
                user_message_id = db.add_message(session_id, message, "user")
                
                # 🎯 SMART ROUTING: Decide between direct LLM vs RAG
                idx_ids = db.get_indexes_for_session(session_id)
                force_rag = bool(data.get("force_rag", False))
                use_rag = True if force_rag else self._should_use_rag(message, idx_ids)

                if run:
                    # Determine reason code based on actual conditions
                    # Use valid enum codes from AgentTracer API
                    if force_rag:
                        routing_reason = "conditional_branch"  # Valid enum
                        routing_confidence = 1.0
                        reasoning = "User explicitly requested RAG mode via force_rag flag"
                        decision_factor = "user_forced"
                    elif use_rag and idx_ids:
                        routing_reason = "conditional_branch"  # Valid enum
                        routing_confidence = 0.85
                        reasoning = f"Query analysis suggests document context needed (has {len(idx_ids)} index(es))"
                        decision_factor = "has_indexed_documents"
                    elif not idx_ids:
                        routing_reason = "fallback_path"  # Valid enum
                        routing_confidence = 1.0
                        reasoning = "No indexed documents - routing to direct LLM"
                        decision_factor = "no_indexes_available"
                    else:
                        routing_reason = "early_exit"  # Valid enum
                        routing_confidence = 0.75
                        reasoning = "Query appears to be general knowledge - direct LLM faster"
                        decision_factor = "general_query"

                    # Check for document-related keywords
                    doc_keywords = ["document", "file", "pdf", "paper", "article", "content"]
                    has_doc_keywords = any(kw in message.lower() for kw in doc_keywords)

                    run.record_decision(
                        decision_type="routing",
                        selected="rag_pipeline" if use_rag else "direct_llm",
                        reason_code=routing_reason,
                        candidates=["rag_pipeline", "direct_llm", "cached_response"],
                        confidence=routing_confidence,
                        step_id=step.step_id,
                        metadata={
                            "forced": force_rag,
                            "decision_factor": decision_factor,
                            "has_indexes": bool(idx_ids),
                            "index_count": len(idx_ids) if idx_ids else 0,
                            "query_length": len(message),
                            "has_doc_keywords": has_doc_keywords,
                            "session_message_count": session.get('message_count', 0),
                            "reasoning": reasoning
                        },
                    )

                    # Tool selection with enhanced metadata
                    run.record_decision(
                        decision_type="tool_selection",
                        selected="rag_api" if use_rag else "ollama_direct",
                        reason_code="accuracy_required" if use_rag else "latency_optimization",
                        candidates=["rag_api", "ollama_direct"],
                        confidence=0.95 if use_rag else 0.90,
                        step_id=step.step_id,
                        metadata={
                            "requires_documents": use_rag,
                            "estimated_latency_ms": 3000 if use_rag else 500,
                            "complexity": "high" if use_rag else "low",
                            "reasoning": "Document retrieval and synthesis required" if use_rag else "Direct generation sufficient"
                        }
                    )
                
                if use_rag:
                    # 🔍 --- Use RAG Pipeline for Document-Related Queries ---
                    print(f"🔍 Using RAG pipeline for document query: '{message[:50]}...'")
                    with _step_ctx(run, "retrieve", "rag_query") as rag_step:
                        response_text, source_docs = self._handle_rag_query(
                            session_id, message, data, idx_ids, run=run, step_id=rag_step.step_id
                        )
                else:
                    # ⚡ --- Use Direct LLM for General Queries (FAST) ---
                    print(f"⚡ Using direct LLM for general query: '{message[:50]}...'")
                    with _step_ctx(run, "tool", "ollama_chat"):
                        response_text, source_docs = self._handle_direct_llm_query(
                            session_id, message, session, run=run
                        )

                # Add AI response to database
                ai_message_id = db.add_message(session_id, response_text, "assistant")
                
                updated_session = db.get_session(session_id)
                
                # Send response with proper error handling
                with _step_ctx(run, "respond", "send_response"):
                    self.send_json_response({
                        "response": response_text,
                        "session": updated_session,
                        "source_documents": source_docs,
                        "used_rag": use_rag
                    })
                
            except BrokenPipeError:
                # Client disconnected - this is normal for long queries, just log it
                print(f"⚠️  Client disconnected during RAG processing for query: '{message[:30]}...'")
            except json.JSONDecodeError:
                if run:
                    run.record_quality_signal(
                        signal_type="schema_valid",
                        signal_code="validation_failed",
                        value=True,
                    )
                    run.record_failure(
                        failure_type="orchestration",
                        failure_code="json_decode_error",
                        message="Invalid JSON payload",
                    )
                self.send_json_response({
                    "error": "Invalid JSON"
                }, status_code=400)
            except Exception as e:
                print(f"❌ Server error in session chat: {str(e)}")
                if run:
                    run.record_failure(
                        failure_type="orchestration",
                        failure_code="server_error",
                        message=f"Unhandled error: {type(e).__name__}",
                    )
                try:
                    self.send_json_response({
                        "error": f"Server error: {str(e)}"
                    }, status_code=500)
                except BrokenPipeError:
                    print(f"⚠️  Client disconnected during error response")
    
    def _should_use_rag(self, message: str, idx_ids: List[str]) -> bool:
        """
        🧠 ENHANCED: Determine if a query should use RAG pipeline using document overviews.
        
        Args:
            message: The user's query
            idx_ids: List of index IDs associated with the session
            
        Returns:
            bool: True if should use RAG, False for direct LLM
        """
        # No indexes = definitely no RAG needed
        if not idx_ids:
            return False

        # Load document overviews for intelligent routing
        try:
            doc_overviews = self._load_document_overviews(idx_ids)
            if doc_overviews:
                return self._route_using_overviews(message, doc_overviews)
        except Exception as e:
            print(f"⚠️ Overview-based routing failed, falling back to simple routing: {e}")
        
        # Fallback to simple pattern matching if overviews unavailable
        return self._simple_pattern_routing(message, idx_ids)

    def _load_document_overviews(self, idx_ids: List[str]) -> List[str]:
        """Load and aggregate overviews for the given index IDs.
        
        Strategy:
        1. Attempt to load each index's dedicated overview file.
        2. Aggregate all overviews found across available files (deduplicated).
        3. If none of the index files exist, fall back to the legacy global overview file.
        """
        import os, json

        aggregated: list[str] = []

        # 1️⃣  Collect overviews from per-index files
        for idx in idx_ids:
            candidate_paths = [
                f"../index_store/overviews/{idx}.jsonl",
                f"index_store/overviews/{idx}.jsonl",
                f"./index_store/overviews/{idx}.jsonl",
            ]
            for p in candidate_paths:
                if os.path.exists(p):
                    print(f"📖 Loading overviews from: {p}")
                    try:
                        with open(p, "r", encoding="utf-8") as f:
                            for line in f:
                                if not line.strip():
                                    continue
                                try:
                                    record = json.loads(line)
                                    overview = record.get("overview", "").strip()
                                    if overview:
                                        aggregated.append(overview)
                                except json.JSONDecodeError:
                                    continue  # skip malformed lines
                        break  # Stop after the first existing path for this idx
                    except Exception as e:
                        print(f"⚠️ Error reading {p}: {e}")
                        break  # Don't keep trying other paths for this idx if read failed

        # 2️⃣  Fall back to legacy global file if no per-index overviews found
        if not aggregated:
            legacy_paths = [
                "../index_store/overviews/overviews.jsonl",
                "index_store/overviews/overviews.jsonl",
                "./index_store/overviews/overviews.jsonl",
            ]
            for p in legacy_paths:
                if os.path.exists(p):
                    print(f"⚠️ Falling back to legacy overviews file: {p}")
                    try:
                        with open(p, "r", encoding="utf-8") as f:
                            for line in f:
                                if not line.strip():
                                    continue
                                try:
                                    record = json.loads(line)
                                    overview = record.get("overview", "").strip()
                                    if overview:
                                        aggregated.append(overview)
                                except json.JSONDecodeError:
                                    continue
                    except Exception as e:
                        print(f"⚠️ Error reading legacy overviews file {p}: {e}")
                    break

        # Limit for performance
        if aggregated:
            print(f"✅ Loaded {len(aggregated)} document overviews from {len(idx_ids)} index(es)")
        else:
            print(f"⚠️ No overviews found for indices {idx_ids}")
        return aggregated[:40]

    def _route_using_overviews(self, query: str, overviews: List[str]) -> bool:
        """
        🎯 Use document overviews and LLM to make intelligent routing decisions.
        
        Returns True if RAG should be used, False for direct LLM.
        """
        if not overviews:
            return False
        
        # Format overviews for the routing prompt
        overviews_block = "\n".join(f"[{i+1}] {ov}" for i, ov in enumerate(overviews))
        
        router_prompt = f"""You are an AI router deciding whether a user question should be answered via:
• "USE_RAG" – search the user's private documents (described below)  
• "DIRECT_LLM" – reply from general knowledge (greetings, public facts, unrelated topics)

CRITICAL PRINCIPLE: When documents exist in the KB, strongly prefer USE_RAG unless the query is purely conversational or completely unrelated to any possible document content.

RULES:
1. If ANY overview clearly relates to the question (entities, numbers, addresses, dates, amounts, companies, technical terms) → USE_RAG
2. For document operations (summarize, analyze, explain, extract, find) → USE_RAG  
3. For greetings only ("Hi", "Hello", "Thanks") → DIRECT_LLM
4. For pure math/world knowledge clearly unrelated to documents → DIRECT_LLM
5. When in doubt → USE_RAG

DOCUMENT OVERVIEWS:
{overviews_block}

DECISION EXAMPLES:
• "What invoice amounts are mentioned?" → USE_RAG (document-specific)
• "Who is PromptX AI LLC?" → USE_RAG (entity in documents)  
• "What is the DeepSeek model?" → USE_RAG (mentioned in documents)
• "Summarize the research paper" → USE_RAG (document operation)
• "What is 2+2?" → DIRECT_LLM (pure math)
• "Hi there" → DIRECT_LLM (greeting only)

USER QUERY: "{query}"

Respond with exactly one word: USE_RAG or DIRECT_LLM"""

        try:
            # Use Ollama to make the routing decision
            response = self.ollama_client.chat(
                message=router_prompt,
                model="qwen3:0.6b",  # Fast model for routing
                enable_thinking=False  # Fast routing
            )
            
            # The response is directly the text, not a dict
            decision = response.strip().upper()
            
            # Parse decision
            if "USE_RAG" in decision:
                print(f"🎯 Overview-based routing: USE_RAG for query: '{query[:50]}...'")
                return True
            elif "DIRECT_LLM" in decision:
                print(f"⚡ Overview-based routing: DIRECT_LLM for query: '{query[:50]}...'")
                return False
            else:
                print(f"⚠️ Unclear routing decision '{decision}', defaulting to RAG")
                return True  # Default to RAG when uncertain
                
        except Exception as e:
            print(f"❌ LLM routing failed: {e}, falling back to pattern matching")
            return self._simple_pattern_routing(query, [])

    def _simple_pattern_routing(self, message: str, idx_ids: List[str]) -> bool:
        """
        📝 FALLBACK: Simple pattern-based routing (original logic).
        """
        message_lower = message.lower()
        
        # Always use Direct LLM for greetings and casual conversation
        greeting_patterns = [
            'hello', 'hi', 'hey', 'greetings', 'good morning', 'good afternoon', 'good evening',
            'how are you', 'how do you do', 'nice to meet', 'pleasure to meet',
            'thanks', 'thank you', 'bye', 'goodbye', 'see you', 'talk to you later',
            'test', 'testing', 'check', 'ping', 'just saying', 'nevermind',
            'ok', 'okay', 'alright', 'got it', 'understood', 'i see'
        ]
        
        # Check for greeting patterns
        for pattern in greeting_patterns:
            if pattern in message_lower:
                return False  # Use Direct LLM for greetings
        
        # Keywords that strongly suggest document-related queries
        rag_indicators = [
            'document', 'doc', 'file', 'pdf', 'text', 'content', 'page',
            'according to', 'based on', 'mentioned', 'states', 'says',
            'what does', 'summarize', 'summary', 'analyze', 'analysis',
            'quote', 'citation', 'reference', 'source', 'evidence',
            'explain from', 'extract', 'find in', 'search for'
        ]
        
        # Check for strong RAG indicators
        for indicator in rag_indicators:
            if indicator in message_lower:
                return True
        
        # Question words + substantial length might benefit from RAG
        question_words = ['what', 'how', 'when', 'where', 'why', 'who', 'which']
        starts_with_question = any(message_lower.startswith(word) for word in question_words)
        
        if starts_with_question and len(message) > 40:
            return True
        
        # Very short messages - use direct LLM
        if len(message.strip()) < 20:
            return False
        
        # Default to Direct LLM unless there's clear indication of document query
        return False
    
    def _handle_direct_llm_query(self, session_id: str, message: str, session: dict, run=None):
        """
        Handle query using direct Ollama client with thinking disabled for speed.
        
        Returns:
            tuple: (response_text, empty_source_docs)
        """
        try:
            # Get conversation history for context
            conversation_history = db.get_conversation_history(session_id)
            
            # Use the session's model or default
            model = session.get('model', 'qwen3:8b')  # Default to fast model
            
            # Direct Ollama call with thinking disabled for speed
            response_text = self.ollama_client.chat(
                message=message,
                model=model,
                conversation_history=conversation_history,
                enable_thinking=False  # ⚡ DISABLE THINKING FOR SPEED
            )
            
            return response_text, []  # No source docs for direct LLM
            
        except Exception as e:
            print(f"❌ Direct LLM error: {e}")
            if run:
                run.record_failure(
                    failure_type="model",
                    failure_code="generation_error",
                    message=f"Direct LLM error: {type(e).__name__}",
                )
            return f"Error processing query: {str(e)}", []
    
    def _handle_rag_query(self, session_id: str, message: str, data: dict, idx_ids: List[str], run=None, step_id=None):
        """
        Handle query using the full RAG pipeline (delegates to the advanced RAG API running on port 8001).

        Returns:
            tuple[str, List[dict]]: (response_text, source_documents)
        """
        # Defaults
        response_text = ""
        source_docs: List[dict] = []

        # Build payload for RAG API
        rag_api_url = RAG_API_CHAT_URL
        table_name = f"text_pages_{idx_ids[-1]}" if idx_ids else None
        payload: Dict[str, Any] = {
            "query": message,
            "session_id": session_id,
        }
        if table_name:
            payload["table_name"] = table_name

        # Copy optional parameters from the incoming request
        optional_params: Dict[str, tuple[type, str]] = {
            "compose_sub_answers": (bool, "compose_sub_answers"),
            "query_decompose": (bool, "query_decompose"),
            "ai_rerank": (bool, "ai_rerank"),
            "context_expand": (bool, "context_expand"),
            "verify": (bool, "verify"),
            "retrieval_k": (int, "retrieval_k"),
            "context_window_size": (int, "context_window_size"),
            "reranker_top_k": (int, "reranker_top_k"),
            "search_type": (str, "search_type"),
            "dense_weight": (float, "dense_weight"),
            "provence_prune": (bool, "provence_prune"),
            "provence_threshold": (float, "provence_threshold"),
        }
        for key, (caster, payload_key) in optional_params.items():
            val = data.get(key)
            if val is not None:
                try:
                    payload[payload_key] = caster(val)  # type: ignore[arg-type]
                except Exception:
                    payload[payload_key] = val

        try:
            rag_response = requests.post(rag_api_url, json=payload)
            if rag_response.status_code == 200:
                rag_data = rag_response.json()
                response_text = rag_data.get("answer", "No answer found.")
                source_docs = rag_data.get("source_documents", [])
                if run and not source_docs:
                    run.record_quality_signal(
                        signal_type="empty_retrieval",
                        signal_code="no_results",
                        value=True,
                        step_id=step_id,
                    )
                    run.record_failure(
                        failure_type="retrieval",
                        failure_code="empty_retrieval",
                        message="RAG returned no source documents",
                        step_id=step_id,
                    )
            else:
                response_text = f"Error from RAG API ({rag_response.status_code}): {rag_response.text}"
                print(f"❌ RAG API error: {response_text}")
                if run:
                    run.record_failure(
                        failure_type="tool",
                        failure_code=f"http_{rag_response.status_code}",
                        message="RAG API returned non-200 response",
                        step_id=step_id,
                    )
        except requests.exceptions.ConnectionError:
            response_text = "Could not connect to the RAG API server. Please ensure it is running."
            print("❌ Connection to RAG API failed (port 8001).")
            if run:
                run.record_failure(
                    failure_type="tool",
                    failure_code="connection_error",
                    message="RAG API connection failed",
                    step_id=step_id,
                )
        except Exception as e:
            response_text = f"Error processing RAG query: {str(e)}"
            print(f"❌ RAG processing error: {e}")
            if run:
                run.record_failure(
                    failure_type="orchestration",
                    failure_code="rag_processing_error",
                    message=f"RAG processing error: {type(e).__name__}",
                    step_id=step_id,
                )

        # Strip any <think>/<thinking> tags that might slip through
        response_text = re.sub(r'<(think|thinking)>.*?</\\1>', '', response_text, flags=re.DOTALL | re.IGNORECASE).strip()

        return response_text, source_docs

    def handle_delete_session(self, session_id: str):
        """Delete a session and its messages"""
        try:
            deleted = db.delete_session(session_id)
            if deleted:
                self.send_json_response({'deleted': deleted})
            else:
                self.send_json_response({'error': 'Session not found'}, status_code=404)
        except Exception as e:
            self.send_json_response({'error': str(e)}, status_code=500)
    
    def handle_file_upload(self, session_id: str):
        """Handle file uploads, save them, and associate with the session."""
        form = parse_multipart_form(self.rfile, self.headers)

        uploaded_files = []
        if 'files' in form:
            files = form['files']
            if not isinstance(files, list):
                files = [files]
            
            upload_dir = "shared_uploads"
            os.makedirs(upload_dir, exist_ok=True)

            for file_item in files:
                if file_item.filename:
                    # Create a unique filename to avoid overwrites
                    unique_filename = f"{uuid.uuid4()}_{file_item.filename}"
                    file_path = os.path.join(upload_dir, unique_filename)
                    
                    with open(file_path, 'wb') as f:
                        f.write(file_item.file.read())
                    
                    # Store the absolute path for the indexing service
                    absolute_file_path = os.path.abspath(file_path)
                    db.add_document_to_session(session_id, absolute_file_path)
                    uploaded_files.append({"filename": file_item.filename, "stored_path": absolute_file_path})

        if not uploaded_files:
            self.send_json_response({"error": "No files were uploaded"}, status_code=400)
            return
            
        self.send_json_response({
            "message": f"Successfully uploaded {len(uploaded_files)} files.",
            "uploaded_files": uploaded_files
        })

    def handle_index_documents(self, session_id: str):
        """Triggers indexing for all documents in a session."""
        print(f"🔥 Received request to index documents for session {session_id[:8]}...")
        try:
            file_paths = db.get_documents_for_session(session_id)
            if not file_paths:
                self.send_json_response({"message": "No documents to index for this session."}, status_code=200)
                return

            print(f"Found {len(file_paths)} documents to index. Sending to RAG API...")
            
            rag_response = requests.post(RAG_API_INDEX_URL, json={"file_paths": file_paths, "session_id": session_id})

            if rag_response.status_code == 200:
                print("✅ RAG API successfully indexed documents.")
                # Merge key config values into index metadata
                idx_meta = {
                    "session_linked": True,
                    "retrieval_mode": "hybrid",
                }
                try:
                    db.update_index_metadata(session_id, idx_meta)  # session_id used as index_id in text table naming
                except Exception as e:
                    print(f"⚠️ Failed to update index metadata for session index: {e}")
                self.send_json_response(rag_response.json())
            else:
                error_info = rag_response.text
                print(f"❌ RAG API indexing failed ({rag_response.status_code}): {error_info}")
                self.send_json_response({"error": f"Indexing failed: {error_info}"}, status_code=500)

        except Exception as e:
            print(f"❌ Exception during indexing: {str(e)}")
            self.send_json_response({"error": f"An unexpected error occurred: {str(e)}"}, status_code=500)
            
    def handle_pdf_upload(self, session_id: str):
        """
        Processes PDF files: extracts text and stores it in the database.
        DEPRECATED: This is the old method. Use handle_file_upload instead.
        """
        # This function is now deprecated in favor of the new indexing workflow
        # but is kept for potential legacy/compatibility reasons.
        # For new functionality, it should not be used.
        self.send_json_response({
            "warning": "This upload method is deprecated. Use the new file upload and indexing flow.",
            "message": "No action taken."
        }, status_code=410) # 410 Gone

    def handle_get_models(self):
        """Get available models from both Ollama and HuggingFace, grouped by capability"""
        try:
            generation_models = []
            embedding_models = []
            
            # Get Ollama models if available
            if self.ollama_client.is_ollama_running():
                all_ollama_models = self.ollama_client.list_models()
                
                # Very naive classification - same logic as RAG API server
                ollama_embedding_models = [m for m in all_ollama_models if any(k in m for k in ['embed','bge','embedding','text'])]
                ollama_generation_models = [m for m in all_ollama_models if m not in ollama_embedding_models]
                
                generation_models.extend(ollama_generation_models)
                embedding_models.extend(ollama_embedding_models)
            
            # Add supported HuggingFace embedding models
            huggingface_embedding_models = [
                "Qwen/Qwen3-Embedding-0.6B",
                "Qwen/Qwen3-Embedding-4B", 
                "Qwen/Qwen3-Embedding-8B"
            ]
            embedding_models.extend(huggingface_embedding_models)
            
            # Sort models for consistent ordering
            generation_models.sort()
            embedding_models.sort()
            
            self.send_json_response({
                "generation_models": generation_models,
                "embedding_models": embedding_models
            })
        except Exception as e:
            self.send_json_response({
                "error": f"Could not list models: {str(e)}"
            }, status_code=500)

    def handle_get_indexes(self):
        try:
            data = db.list_indexes()
            self.send_json_response({'indexes': data, 'total': len(data)})
        except Exception as e:
            self.send_json_response({'error': str(e)}, status_code=500)
    
    def handle_get_index(self, index_id: str):
        try:
            data = db.get_index(index_id)
            if not data:
                self.send_json_response({'error': 'Index not found'}, status_code=404)
                return
            self.send_json_response(data)
        except Exception as e:
            self.send_json_response({'error': str(e)}, status_code=500)
    
    def handle_create_index(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            name = data.get('name')
            description = data.get('description')
            metadata = data.get('metadata', {})
            
            if not name:
                self.send_json_response({'error': 'Name required'}, status_code=400)
                return
            
            # Add complete metadata from RAG system configuration if available
            if RAG_SYSTEM_AVAILABLE and PIPELINE_CONFIGS.get('default'):
                default_config = PIPELINE_CONFIGS['default']
                complete_metadata = {
                    'status': 'created',
                    'metadata_source': 'rag_system_config',
                    'created_at': json.loads(json.dumps(datetime.now().isoformat())),
                    'chunk_size': 512,  # From default config
                    'chunk_overlap': 64,  # From default config
                    'retrieval_mode': 'hybrid',  # From default config
                    'window_size': 5,  # From default config
                    'embedding_model': 'Qwen/Qwen3-Embedding-0.6B',  # From default config
                    'enrich_model': 'qwen3:0.6b',  # From default config
                    'overview_model': 'qwen3:0.6b',  # From default config
                    'enable_enrich': True,  # From default config
                    'latechunk': True,  # From default config
                    'docling_chunk': True,  # From default config
                    'note': 'Default configuration from RAG system'
                }
                # Merge with any provided metadata
                complete_metadata.update(metadata)
                metadata = complete_metadata
            
            idx_id = db.create_index(name, description, metadata)
            self.send_json_response({'index_id': idx_id}, status_code=201)
        except ValueError as e:
            # Handle duplicate index name or other validation errors
            self.send_json_response({'error': str(e)}, status_code=409)
        except Exception as e:
            self.send_json_response({'error': str(e)}, status_code=500)
    
    def handle_index_file_upload(self, index_id: str):
        """Reuse file upload logic but store docs under index."""
        form = parse_multipart_form(self.rfile, self.headers)
        uploaded_files=[]
        if 'files' in form:
            files=form['files']
            if not isinstance(files, list):
                files=[files]
            upload_dir='shared_uploads'
            os.makedirs(upload_dir, exist_ok=True)
            for f in files:
                if f.filename:
                    unique=f"{uuid.uuid4()}_{f.filename}"
                    path=os.path.join(upload_dir, unique)
                    with open(path,'wb') as out: out.write(f.file.read())
                    db.add_document_to_index(index_id, f.filename, os.path.abspath(path))
                    uploaded_files.append({'filename':f.filename,'stored_path':os.path.abspath(path)})
        if not uploaded_files:
            self.send_json_response({'error':'No files uploaded'}, status_code=400); return
        self.send_json_response({'message':f"Uploaded {len(uploaded_files)} files","uploaded_files":uploaded_files})
    
    def handle_build_index(self, index_id: str):
        try:
            index=db.get_index(index_id)
            if not index:
                self.send_json_response({'error':'Index not found'}, status_code=404); return
            file_paths=[d['stored_path'] for d in index.get('documents',[])]
            if not file_paths:
                self.send_json_response({'error':'No documents to index'}, status_code=400); return

            # Parse request body for optional flags and configuration
            latechunk = False
            docling_chunk = False
            chunk_size = 512
            chunk_overlap = 64
            retrieval_mode = 'hybrid'
            window_size = 2
            enable_enrich = True
            embedding_model = None
            enrich_model = None
            batch_size_embed = 50
            batch_size_enrich = 25
            overview_model = None
            
            if 'Content-Length' in self.headers and int(self.headers['Content-Length']) > 0:
                try:
                    length = int(self.headers['Content-Length'])
                    body = self.rfile.read(length)
                    opts = json.loads(body.decode('utf-8'))
                    latechunk = bool(opts.get('latechunk', False))
                    docling_chunk = bool(opts.get('doclingChunk', False))
                    chunk_size = int(opts.get('chunkSize', 512))
                    chunk_overlap = int(opts.get('chunkOverlap', 64))
                    retrieval_mode = str(opts.get('retrievalMode', 'hybrid'))
                    window_size = int(opts.get('windowSize', 2))
                    enable_enrich = bool(opts.get('enableEnrich', True))
                    embedding_model = opts.get('embeddingModel')
                    enrich_model = opts.get('enrichModel')
                    batch_size_embed = int(opts.get('batchSizeEmbed', 50))
                    batch_size_enrich = int(opts.get('batchSizeEnrich', 25))
                    overview_model = opts.get('overviewModel')
                except Exception:
                    # Keep defaults on parse error
                    pass

            # Set per-index overview file path
            overview_path = f"index_store/overviews/{index_id}.jsonl"

            # Ensure config_override includes overview_path
            def ensure_overview_path(cfg: dict):
                cfg["overview_path"] = overview_path
            
            # we'll inject later when we build config_override

            # Delegate to advanced RAG API same as session indexing
            rag_api_url = RAG_API_INDEX_URL
            import requests, json as _json
            # Use the index's dedicated LanceDB table so retrieval matches
            table_name = index.get("vector_table_name")
            payload = {
                "file_paths": file_paths,
                "session_id": index_id,  # reuse index_id for progress tracking
                "table_name": table_name,
                "chunk_size": chunk_size,
                "chunk_overlap": chunk_overlap,
                "retrieval_mode": retrieval_mode,
                "window_size": window_size,
                "enable_enrich": enable_enrich,
                "batch_size_embed": batch_size_embed,
                "batch_size_enrich": batch_size_enrich
            }
            if latechunk:
                payload["enable_latechunk"] = True
            if docling_chunk:
                payload["enable_docling_chunk"] = True
            if embedding_model:
                payload["embedding_model"] = embedding_model
                payload["embeddingModel"] = embedding_model
            if enrich_model:
                payload["enrich_model"] = enrich_model
                payload["enrichModel"] = enrich_model
            if overview_model:
                payload["overview_model_name"] = overview_model
                payload["overviewModel"] = overview_model
                
            rag_resp = requests.post(rag_api_url, json=payload)
            if rag_resp.status_code==200:
                meta_updates = {
                    "chunk_size": chunk_size,
                    "chunk_overlap": chunk_overlap,
                    "retrieval_mode": retrieval_mode,
                    "window_size": window_size,
                    "enable_enrich": enable_enrich,
                    "latechunk": latechunk,
                    "docling_chunk": docling_chunk,
                }
                if embedding_model:
                    meta_updates["embedding_model"] = embedding_model
                if enrich_model:
                    meta_updates["enrich_model"] = enrich_model
                if overview_model:
                    meta_updates["overview_model"] = overview_model
                try:
                    db.update_index_metadata(index_id, meta_updates)
                except Exception as e:
                    print(f"⚠️ Failed to update index metadata: {e}")

                self.send_json_response({
                    "response": rag_resp.json(),
                    **meta_updates
                })
            else:
                # Gracefully handle scenario where table already exists (idempotent build)
                try:
                    err_json = rag_resp.json()
                except Exception:
                    err_json = {}
                err_text = err_json.get('error') if isinstance(err_json, dict) else rag_resp.text
                if err_text and 'already exists' in err_text:
                    # Treat as non-fatal; return message indicating index previously built
                    self.send_json_response({
                        "message": "Index already built – skipping rebuild.",
                        "note": err_text
                })
                else:
                    self.send_json_response({"error":f"RAG indexing failed: {rag_resp.text}"}, status_code=500)
        except Exception as e:
            self.send_json_response({'error':str(e)}, status_code=500)
    
    def handle_link_index_to_session(self, session_id: str, index_id: str):
        try:
            db.link_index_to_session(session_id, index_id)
            self.send_json_response({'message':'Index linked to session'})
        except Exception as e:
            self.send_json_response({'error':str(e)}, status_code=500)

    def handle_get_session_indexes(self, session_id: str):
        try:
            idx_ids = db.get_indexes_for_session(session_id)
            indexes = []
            for idx_id in idx_ids:
                idx = db.get_index(idx_id)
                if idx:
                    # Try to populate metadata for older indexes that have empty metadata
                    if not idx.get('metadata') or len(idx['metadata']) == 0:
                        print(f"🔍 Attempting to infer metadata for index {idx_id[:8]}...")
                        inferred_metadata = db.inspect_and_populate_index_metadata(idx_id)
                        if inferred_metadata:
                            # Refresh the index data with the new metadata
                            idx = db.get_index(idx_id)
                    indexes.append(idx)
            self.send_json_response({'indexes': indexes, 'total': len(indexes)})
        except Exception as e:
            self.send_json_response({'error': str(e)}, status_code=500)

    def handle_delete_index(self, index_id: str):
        """Remove an index, its documents, links, and the underlying LanceDB table."""
        try:
            deleted = db.delete_index(index_id)
            if deleted:
                self.send_json_response({'message': 'Index deleted successfully', 'index_id': index_id})
            else:
                self.send_json_response({'error': 'Index not found'}, status_code=404)
        except Exception as e:
            self.send_json_response({'error': str(e)}, status_code=500)

    def handle_rename_session(self, session_id: str):
        """Rename an existing session title"""
        try:
            session = db.get_session(session_id)
            if not session:
                self.send_json_response({"error": "Session not found"}, status_code=404)
                return

            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.send_json_response({"error": "Request body required"}, status_code=400)
                return

            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            new_title: str = data.get('title', '').strip()

            if not new_title:
                self.send_json_response({"error": "Title cannot be empty"}, status_code=400)
                return

            db.update_session_title(session_id, new_title)
            updated_session = db.get_session(session_id)

            self.send_json_response({
                "message": "Session renamed successfully",
                "session": updated_session
            })

        except json.JSONDecodeError:
            self.send_json_response({"error": "Invalid JSON"}, status_code=400)
        except Exception as e:
            self.send_json_response({"error": f"Failed to rename session: {str(e)}"}, status_code=500)

    def send_json_response(self, data, status_code: int = 200):
        """Send a JSON (UTF-8) response with CORS headers. Safe against client disconnects."""
        try:
            self.send_response(status_code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
            self.send_header('Access-Control-Allow-Credentials', 'true')
            self.end_headers()
        
            response_bytes = json.dumps(data, indent=2).encode('utf-8')
            self.wfile.write(response_bytes)
        except BrokenPipeError:
            # Client disconnected before we could finish sending
            print("⚠️  Client disconnected during response – ignoring.")
        except Exception as e:
            print(f"❌ Error sending response: {e}")
    
    def log_message(self, format, *args):
        """Custom log format"""
        print(f"[{self.date_time_string()}] {format % args}")

def main():
    """Main function to initialize and start the server"""
    PORT = 8100  # 🆕 Define port
    try:
        # Initialize the database
        print("✅ Database initialized successfully")

        # Initialize the PDF processor
        try:
            pdf_module.initialize_simple_pdf_processor()
            print("📄 Initializing simple PDF processing...")
            if pdf_module.simple_pdf_processor:
                print("✅ Simple PDF processor initialized")
            else:
                print("⚠️ PDF processing could not be initialized.")
        except Exception as e:
            print(f"❌ Error initializing PDF processor: {e}")
            print("⚠️ PDF processing disabled - server will run without RAG functionality")

        # Set a global reference to the initialized processor if needed elsewhere
        global pdf_processor
        pdf_processor = pdf_module.simple_pdf_processor
        if pdf_processor:
            print("✅ Global PDF processor initialized")
        else:
            print("⚠️ PDF processing disabled - server will run without RAG functionality")
        
        # Cleanup empty sessions on startup
        print("🧹 Cleaning up empty sessions...")
        cleanup_count = db.cleanup_empty_sessions()
        if cleanup_count > 0:
            print(f"✨ Cleaned up {cleanup_count} empty sessions")
        else:
            print("✨ No empty sessions to clean up")

        # Start the server
        with ReusableTCPServer(("", PORT), ChatHandler) as httpd:
            print(f"🚀 Starting localGPT backend server on port {PORT}")
            print(f"📍 Chat endpoint: http://localhost:{PORT}/chat")
            print(f"🔍 Health check: http://localhost:{PORT}/health")
            
            # Test Ollama connection
            client = OllamaClient()
            if client.is_ollama_running():
                models = client.list_models()
                print(f"✅ Ollama is running with {len(models)} models")
                print(f"📋 Available models: {', '.join(models[:3])}{'...' if len(models) > 3 else ''}")
            else:
                print("⚠️  Ollama is not running. Please start Ollama:")
                print("   Install: https://ollama.ai")
                print("   Run: ollama serve")
            
            print(f"\n🌐 Frontend should connect to: http://localhost:{PORT}")
            print("💬 Ready to chat!\n")
            
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")

if __name__ == "__main__":
    main() 
