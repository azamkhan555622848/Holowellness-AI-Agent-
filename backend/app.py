from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import os
import logging
import uuid
from dotenv import load_dotenv
import concurrent.futures
from memory_manager import memory_manager
from bson.json_util import dumps
from bson import ObjectId, errors
from sync_rag_pdfs import sync_pdfs_from_s3
from s3_cache import try_download_caches, try_upload_caches
from lambda_client import LambdaIndexingClient
import re

# Load environment variables
load_dotenv()

# Production configuration
FLASK_ENV = os.getenv('FLASK_ENV', 'development')
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# RAG/S3 configuration
# Allow RAG sync on start to be controlled purely by env var in all environments
RAG_SYNC_ON_START = os.getenv('RAG_SYNC_ON_START', 'false').lower() == 'true'
RAG_S3_BUCKET = os.getenv('RAG_S3_BUCKET', 'holowellness')
RAG_S3_PREFIX = os.getenv('RAG_S3_PREFIX', 'rag_pdfs/')  # default to folder 'rag_pdfs/'

# Configure logging
log_level = os.getenv('LOG_LEVEL', 'INFO')
logging.basicConfig(level=getattr(logging, log_level.upper()))
logger = logging.getLogger(__name__)

# Import enhanced RAG system with BGE reranking (gated by env to reduce memory usage on low-RAM hosts)
# MEMORY OPTIMIZATION: Default to lightweight RAG. Allow an explicit override to enable in production when resources permit.
ALLOW_ENHANCED_IN_PROD = os.getenv('ALLOW_ENHANCED_RAG_IN_PROD', 'false').lower() == 'true'
if FLASK_ENV == 'production' and not ALLOW_ENHANCED_IN_PROD:
    ENABLE_ENHANCED_RAG = False
else:
    ENABLE_ENHANCED_RAG = os.getenv('ENABLE_ENHANCED_RAG', 'false').lower() == 'true'
try:
    if ENABLE_ENHANCED_RAG:
        from enhanced_rag_qwen import EnhancedRAGSystem
        USE_ENHANCED_RAG = True
        logger = logging.getLogger(__name__)
        logger.info("Enhanced RAG system with BGE reranking is enabled")
    else:
        raise ImportError("Enhanced RAG disabled via ENABLE_ENHANCED_RAG=false")
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"Enhanced RAG disabled/unavailable ({e}). Using original RAG system")
    from rag_qwen import RAGSystem
    USE_ENHANCED_RAG = False

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['DEBUG'] = DEBUG

# Configure CORS based on environment
if FLASK_ENV == 'production':
    cors_origins = os.getenv('CORS_ORIGINS', '').split(',')
    CORS(app, resources={r"/api/*": {"origins": cors_origins}}, supports_credentials=True)
    logger.info(f"Production CORS configured for origins: {cors_origins}")
else:
    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)
    logger.info("Development CORS configured for all origins")

# Create static directory if it doesn't exist
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)

# Health check endpoint for AWS Load Balancer
@app.route('/health')
def health_check():
    try:
        # Basic health checks
        checks = {
            'status': 'healthy',
            'service': 'holowellness-api',
            'version': '1.0',
            'environment': FLASK_ENV,
            'openrouter_configured': bool(os.getenv('OPENROUTER_API_KEY')),
            'mongodb_configured': bool(os.getenv('MONGO_URI')),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Test MongoDB connection (lightweight ping)
        try:
            if memory_manager.mongo_client is not None:
                memory_manager.mongo_client.admin.command('ping')
                checks['mongodb_status'] = 'connected'
            else:
                checks['mongodb_status'] = 'error: MongoDB client not initialized'
        except Exception as e:
            checks['mongodb_status'] = f'error: {str(e)}'
            
        return jsonify(checks), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

# Initialize the RAG system (Enhanced or Original) with error handling
PDF_DIR = os.path.join(os.path.dirname(__file__), "pdfs")
logger.info(f"Initializing RAG system with documents from: {PDF_DIR}")
logger.info(f"RAG S3 source: bucket='{RAG_S3_BUCKET}', prefix='{RAG_S3_PREFIX}'")

rag = None
rag_error = None

try:
    # Create PDFs directory if it doesn't exist
    os.makedirs(PDF_DIR, exist_ok=True)
    
    if USE_ENHANCED_RAG:
        # Use enhanced RAG with BGE reranking
        rag = EnhancedRAGSystem(pdf_dir=PDF_DIR)
        logger.info("✅ Enhanced RAG system with BGE reranking initialized successfully")
    else:
        # Fall back to original RAG system - allow initialization even with no PDFs
        rag = RAGSystem(PDF_DIR)
        logger.info("⚠️ Using original RAG system (no reranking)")
        
    # Log document count
    doc_count = len(rag.documents) if hasattr(rag, 'documents') and rag.documents else 0
    logger.info(f"📊 RAG system initialized with {doc_count} documents")
    
except Exception as e:
    logger.error(f"❌ RAG system initialization failed: {e}", exc_info=True)
    rag_error = str(e)
    rag = None
    logger.info("🔄 Flask app will continue without RAG system")

# Optionally sync PDFs from S3 and rebuild indices at startup
try:
    if rag is not None and RAG_SYNC_ON_START:
        logger.info(
            f"📥 RAG_SYNC_ON_START enabled. Syncing PDFs from S3 bucket '{RAG_S3_BUCKET}' prefix '{RAG_S3_PREFIX}'..."
        )
        # Always sync on start to ensure only expected PDFs are present
        sync_pdfs_from_s3()
        try:
            if hasattr(rag, 'documents'):
                rag.documents = []
            if hasattr(rag, 'vector_store'):
                rag.vector_store = None
            if hasattr(rag, 'bm25_index'):
                rag.bm25_index = None
            # Try S3 caches first
            if try_download_caches(rag):
                # Load caches into memory
                rag._load_or_create_embeddings()
            else:
                rag._ingest_documents()
                rag._save_embeddings()
                try_upload_caches(rag)
            logger.info("✅ Startup PDF sync & embedding cache built")
        except Exception as reindex_err:
            logger.error(f"Failed to build embeddings after sync: {reindex_err}")
except Exception as sync_err:
    logger.error(f"Startup sync error: {sync_err}")

DEFAULT_CHATBOT_ID = "664123456789abcdef123456"

# Optional: allow disabling reranker via env if enhanced RAG is used
try:
    if USE_ENHANCED_RAG and rag is not None and os.getenv('DISABLE_RERANKER', 'false').lower() == 'true':
        if hasattr(rag, 'reranker'):
            rag.reranker = None
        if hasattr(rag, 'reranker_model_name'):
            rag.reranker_model_name = None
        logger.warning("DISABLE_RERANKER=true → Reranker disabled at runtime")
except Exception:
    logger.exception("Failed to apply DISABLE_RERANKER flag")


def _detect_language(text: str) -> str:
    """Very small heuristic to detect if user is writing in Chinese vs English."""
    if re.search(r"[\u4e00-\u9fff]", text):
        return "zh"
    return "en"


def _looks_general_query(q: str) -> str:
    """Detect general-capability or topic-reset style user queries."""
    ql = (q or "").lower().strip()
    general_triggers = [
        "how can you help", "what can you do", "in general",
        "switch topic", "new topic", "change topic", "talk about something else",
        "general help", "help in general"
    ]
    return any(p in ql for p in general_triggers)

def _classify_intent(query: str, history: list) -> str:
    """Intent tagging that down-weights old history and respects general/topic-switch queries."""
    if _looks_general_query(query):
        return "general"

    # Consider only recent history for topic inference
    window = int(os.getenv('RAG_HISTORY_WINDOW', '10'))
    recent = (history or [])[-window:]
    recent_text = (" ".join([m.get("content", "") for m in recent]) if recent else "").lower()

    # Topic keyword sets
    knee_terms = {"knee", "kneecap", "patella", "patellofemoral", "pfps", "膝", "膝蓋", "膝盖", "髕骨", "髌骨", "前膝"}
    back_terms = {"back", "back pain", "lumbar", "sciatica", "腰", "下背", "背痛"}
    shoulder_terms = {"shoulder", "rotator", "impingement", "肩", "肩膀"}

    # Only bias by history if the current query overlaps the topic
    import re as _re
    query_tokens = set(_re.findall(r"\w+", (query or "").lower()))
    best_topic, best_hits = "general", 0
    topics = [("knee_pain", knee_terms), ("back_pain", back_terms), ("shoulder_pain", shoulder_terms)]
    for topic_name, kws in topics:
        if len(query_tokens & kws) == 0:
            continue  # no overlap with current query
        hits = sum(1 for kw in kws if kw in recent_text or kw in query_tokens)
        if hits > best_hits:
            best_topic, best_hits = topic_name, hits
    return best_topic if best_hits > 0 else "general"


def _is_followup(history: list, latest_user_message: str) -> bool:
    """Be conservative: treat as follow-up only if the user likely answered the last question."""
    if not history:
        return False
    user_l = (latest_user_message or "").strip().lower()
    # If the user is asking a new question, it's not a follow-up answer
    if "?" in user_l:
        return False
    last_two = history[-2:]
    last_assistant = next((m for m in reversed(last_two) if m.get("role") == "assistant"), None)
    if not last_assistant:
        return False
    a_q = (last_assistant.get("content", "") or "").lower()
    import re as _re
    # Numeric scale questions
    if any(tok in a_q for tok in ["/10", "scale", "rate"]):
        return bool(_re.search(r"\b([0-9]|10)\b", user_l))
    # Yes/No slot questions
    slot_hints = ["swelling", "clicking", "locking", "red flag", "fever", "stairs", "activity", "worse", "better"]
    if any(s in a_q for s in slot_hints):
        return any(tok in user_l for tok in ["yes", "no", "yup", "nope", "yeah", "nah", "y", "n"])
    return False

@app.route('/', methods=['GET'])
def index():
    """Serve the static HTML file"""
    return send_from_directory('static', 'index.html')

@app.route('/api', methods=['GET'])
def api_info():
    """Root route for status check and basic instructions"""
    enhanced_info = ""
    if USE_ENHANCED_RAG and hasattr(rag, 'reranker') and rag.reranker:
        enhanced_info = " with BGE Reranking (Two-Stage Retrieval)"
    elif USE_ENHANCED_RAG:
        enhanced_info = " (Enhanced RAG - Reranker Loading)"
    
    rag_status = "Not Available"
    rag_info = {'type': 'Error', 'error': rag_error} if rag_error else {'type': 'Not Initialized'}
    
    if rag is not None:
        rag_status = "Available"
        rag_info = {
            'type': 'Enhanced RAG with BGE Reranking' if USE_ENHANCED_RAG else 'Original RAG',
            'reranker_active': bool(USE_ENHANCED_RAG and hasattr(rag, 'reranker') and rag.reranker),
            'reranker_model': rag.reranker_model_name if USE_ENHANCED_RAG and hasattr(rag, 'reranker_model_name') else None,
            'stage1_candidates': rag.first_stage_k if USE_ENHANCED_RAG and hasattr(rag, 'first_stage_k') else 'N/A',
            'final_results': rag.final_k if USE_ENHANCED_RAG and hasattr(rag, 'final_k') else 'N/A'
        }

    return jsonify({
        'status': 'ok',
        'message': f'HoloWellness Chatbot API is running with DeepSeek-R1-Distill-Qwen-14B{enhanced_info}',
        'rag_status': rag_status,
        'rag_system': rag_info,
        'rag_s3': {
            'bucket': RAG_S3_BUCKET,
            'prefix': RAG_S3_PREFIX
        },
        'endpoints': {
            '/api/chat': 'POST - Send a query to get a response from the enhanced chatbot',
            '/api/health': 'GET - Check if the API is running',
            '/api/memory': 'GET - Get memory for a session',
            '/api/memory/clear': 'POST - Clear memory for a session',
            '/api/rag/reindex': 'POST - Force reindexing of documents'
        },
        'documents_indexed': len(rag.documents) if rag and hasattr(rag, 'documents') else 0
    })

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        # Strict JSON parsing with better error handling
        try:
            data = request.get_json(force=True, silent=False)
        except Exception:
            logger.exception("Invalid JSON in request")
            return jsonify({'error': 'Invalid JSON'}), 400
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Accept both 'query' and 'message' for compatibility
        query = data.get('query') or data.get('message', '').strip()
        
        # Extract multimodal inputs for RAG
        metrics = data.get('metrics')
        image_url = data.get('image_url')
        image_base64 = data.get('image_base64')

        user_id = data.get('user_id')
        session_id = data.get('session_id')
        # Per-request translation toggle (default True)
        translate_flag = data.get('translate')
        translate = True if translate_flag is None else bool(translate_flag)
        # Optional per-request model override (must be allowed by server-side list)
        model_override = data.get('model')

        if not query:
            return jsonify({'error': 'Field "query" or "message" is required'}), 400

        # Generate user_id if not provided (for in-memory fallback)
        if not user_id:
            user_id = str(uuid.uuid4())
            logger.info(f"Generated user_id for session: {user_id}")

        # Validate user_id for MongoDB if available
        if memory_manager.mongodb_available:
            try:
                user_object_id = ObjectId(user_id)
            except Exception:
                return jsonify({'error': 'Invalid user_id'}), 400

        # Create or validate session - auto-recover from invalid sessions
        if not session_id or session_id.strip() == "":
            session_id = str(uuid.uuid4()) if not memory_manager.mongodb_available else str(ObjectId())
            session_doc = memory_manager._create_session_document(
                session_id, user_id, DEFAULT_CHATBOT_ID, "Default Chat Session"
            )
            logger.info(f"Created new session: {session_id}")
        else:
            # Validate existing session, create new if invalid
            session_doc = memory_manager._get_session_document(session_id)
            if not session_doc:
                logger.warning(f"Invalid session_id {session_id}, creating new session")
                session_id = str(uuid.uuid4()) if not memory_manager.mongodb_available else str(ObjectId())
                session_doc = memory_manager._create_session_document(
                    session_id, user_id, DEFAULT_CHATBOT_ID, "Default Chat Session"
                )
                logger.info(f"Created recovery session: {session_id}")

        logger.info(f"Received query for session {session_id} from user {user_id}: {query}")
        chat_session = memory_manager._get_session_document(session_id)
        chatbot_id = chat_session["chatbot"]
        memory_manager.add_user_message(session_id, query, user_id=user_id)

        # Check if RAG system is available
        if rag is None:
            error_msg = f"RAG system not available: {rag_error}" if rag_error else "RAG system not initialized"
            logger.error(error_msg)
            return jsonify({'error': error_msg}), 500

        conversation_history = memory_manager.get_chat_history(session_id)
        # Build a compact pinned summary to preserve key facts beyond the sliding window
        pinned_summary = memory_manager.get_pinned_summary(session_id)
        # Retrieve long-term memory facts related to the query
        long_term_facts = memory_manager.retrieve_long_term_memory(session_id, query)
        if long_term_facts:
            conversation_history.insert(0, {
                "role": "system",
                "content": "LONG_TERM_MEMORY:\n" + "\n".join(long_term_facts)
            })
        try:
            # Check if RAG is disabled - go straight to fallback
            if os.getenv('DISABLE_RAG', 'false').lower() == 'true':
                logger.info("🚫 RAG disabled via DISABLE_RAG=true, using direct LLM")
                raise Exception("RAG disabled - using direct LLM fallback")
            
            # Remote Gemma RAG integration (feature-flagged)
            if os.getenv('USE_REMOTE_GEMMA_RAG', 'false').lower() == 'true':
                remote_url = os.getenv('GEMMA_RAG_URL')
                if not remote_url:
                    raise Exception('USE_REMOTE_GEMMA_RAG=true but GEMMA_RAG_URL is not set')
                payload = {
                    'query': query,
                    'history': conversation_history[-6:] if conversation_history else [],
                    'translate': translate,
                    'top_k': int(os.getenv('RAG_TOPK', '5')),
                    'metrics': metrics,
                    'image_url': image_url,
                    'image_base64': image_base64
                }
                logger.info(f"Calling remote Gemma RAG service: {remote_url}")
                r = requests.post(remote_url, json=payload, timeout=int(os.getenv('GEMMA_RAG_TIMEOUT', '60')))
                if r.status_code != 200:
                    raise Exception(f"Remote RAG HTTP {r.status_code}: {r.text[:200]}")
                response_data = r.json()
            else:
                logger.info(f"🤖 Starting RAG generation for query: {query[:50]}...")
                logger.info(f"🔧 RAG system available: {rag is not None}")
                logger.info(f"🔑 OpenRouter API Key configured: {bool(os.getenv('OPENROUTER_API_KEY'))}")

                # Enforce a soft timeout around RAG end-to-end generation
                rag_timeout_s = int(os.getenv('RAG_TIMEOUT_SECONDS', '45'))
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    # Add lightweight routing hints to steer the model
                    user_lang = _detect_language(query)
                    intent_tag = _classify_intent(query, conversation_history)
                    expecting_followup = _is_followup(conversation_history, query)
                    topic_reset = _looks_general_query(query) or intent_tag == 'general'
                    routing_hint = (
                        f"ROUTING_HINTS:\nintent={intent_tag}\n"
                        f"user_language={'zh-TW' if user_lang=='zh' else 'en'}\n"
                        f"followup_mode={'true' if expecting_followup else 'false'}\n"
                        f"topic_reset={'true' if topic_reset else 'false'}\n"
                        "If topic_reset=true, do not continue prior intake; answer the new question or give general capabilities. "
                        "Focus strictly on the patient's current complaint unless the user requests general help or switches topic. "
                        "If followup_mode=true, interpret the user's message as an answer to your prior question and move to the next most relevant diagnostic step."
                    )
                    # Build augmented history with pinned summary; minimize complaint slots on topic reset
                    def _minimal_pinned(summary: str) -> str:
                        lines = [ln for ln in (summary or '').splitlines() if ln.strip()]
                        kept = [ln for ln in lines if not ln.startswith('AnsweredSlots:') and not ln.startswith('UnansweredSlots:')]
                        return "\n".join(kept)

                    augmented_history = []
                    eff_summary = pinned_summary
                    if topic_reset:
                        eff_summary = _minimal_pinned(pinned_summary)
                    if eff_summary.strip():
                        augmented_history.append({
                            "role": "system",
                            "content": f"LONG_TERM_MEMORY:\n{eff_summary}"
                        })
                    if topic_reset and conversation_history:
                        short_win = conversation_history[-3:] if len(conversation_history) > 3 else conversation_history
                        augmented_history.extend(short_win)
                    else:
                        augmented_history.extend(conversation_history)
                    augmented_history.append({"role": "system", "content": routing_hint})

                    future = executor.submit(rag.generate_answer, query, augmented_history, None, None, translate, model_override)
                    try:
                        response_data = future.result(timeout=rag_timeout_s)
                    except concurrent.futures.TimeoutError:
                        raise Exception(f"RAG timeout after {rag_timeout_s}s")

            content = response_data.get("content", "")
            # Hide chain-of-thought unless explicitly enabled
            expose_thinking = os.getenv('EXPOSE_THINKING', 'false').lower() == 'true'
            thinking = response_data.get("thinking", "") if expose_thinking else ""
            retrieved_context = response_data.get("retrieved_context", "")
            response_mode = None

            logger.info(f"✅ RAG generation successful, content length: {len(content)}")
            # If upstream returned an empty string, force fallback to direct OpenRouter to avoid blank first replies
            if not str(content).strip():
                raise Exception("Empty content from RAG pipeline")
        except Exception as e:
            logger.error(f"❌ RAG/LLM generation error: {e}", exc_info=True)
            logger.error(f"🔍 Error type: {type(e).__name__}")
            logger.error(f"🔍 Error details: {str(e)}")
            
            # FALLBACK: Try direct OpenRouter API call without RAG
            logger.info("🔄 Attempting fallback: Direct OpenRouter API call...")
            try:
                import requests
                import json
                
                api_key = os.getenv('OPENROUTER_API_KEY')
                if not api_key:
                    raise Exception("No OpenRouter API key available")
                
                # System prompt to ensure clinically-sound, concise guidance with structured intake/direct-answer policy
                messages = [
                    {
                        "role": "system",
                        "content": (
                            "You are Dr. HoloWellness, an experienced wellness/medical/fitness clinician speaking directly to your patient. "
                            f"Respond in {'Traditional Chinese' if _detect_language(query)=='zh' else 'English'} only. "
                            f"Primary intent: {_classify_intent(query, conversation_history)}. Stay strictly on-topic for this intent. "
                            "If the user seems to answer your previous question, acknowledge briefly and move to the next most relevant step. "

                            "INTERVIEW POLICY (slot-filling): If the message is a direct, specific question that can be answered safely, answer immediately. Otherwise, ask 2–3 concise, targeted questions to gather missing key slots (onset/duration, location, quality, severity 0–10, radiation, aggravating/relieving factors, associated symptoms, functional impact, history, meds/allergies, red flags; or for fitness: goal, experience, constraints/injuries, equipment, schedule). Escalate if red flags. "

                            "OUTPUT MODES: (1) Intake-first mode when info is insufficient: Acknowledge, then 2–3 short follow-up questions (bulleted/numbered), optional 1 safety tip; no full plan yet. (2) Direct-answer mode when sufficient info or a simple question: Follow STRICTLY—1) Empathetic acknowledgment (1 sentence); 2) Brief assessment (1–2 sentences); 3) Two specific, actionable recommendations; 4) One relevant follow-up question. "

                            "TONE: Professional, warm, concise, evidence-informed, safety-aware. Tailor to provided details (age, activity, conditions, meds). Minimize repetition across turns. "
                        ),
                    }
                ]
                
                # Add conversation history (limited to last 6 messages to capture prior Q/A)
                for msg in conversation_history[-6:]:
                    messages.append(msg)
                
                # Add current user query
                messages.append({"role": "user", "content": query})
                
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    # Helpful for OpenRouter routing/allowlist
                    "HTTP-Referer": os.getenv('APP_PUBLIC_URL', 'http://127.0.0.1'),
                    "X-Title": os.getenv('APP_TITLE', 'HoloWellness Chatbot')
                }
                
                # Use the same/deploy-compatible model as main RAG path, configurable via env
                model_name = (model_override or os.getenv('OPENROUTER_MODEL', 'deepseek/deepseek-r1-distill-qwen-14b'))
                max_tokens_env = int(os.getenv('OPENROUTER_MAX_TOKENS', '1000'))
                data = {
                    "model": model_name,
                    "messages": messages,
                    "max_tokens": max_tokens_env,
                    "temperature": 0.1
                }
                
                logger.info("🌐 Making direct OpenRouter API call...")
                response = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=int(os.getenv('OPENROUTER_TIMEOUT', '60'))
                )
                
                if response.status_code == 200:
                    result = response.json()
                    english_content = result['choices'][0]['message']['content']
                    thinking = "Direct API call (RAG system unavailable)"
                    retrieved_context = "No document retrieval (fallback mode)"
                    
                    # IMPORTANT: Apply translation layer to fallback mode too
                    try:
                        # Use the same translation function as RAG system
                        if rag and hasattr(rag, '_translate_to_traditional_chinese'):
                            logger.info("🔄 Applying translation layer to fallback response...")
                            translated_content = rag._translate_to_traditional_chinese(english_content)
                        else:
                            # Fallback translation using direct API call to translation model
                            logger.info("🔄 Using direct translation for fallback...")
                            translation_prompt = f"""請將以下英文醫療建議翻譯成繁體中文。保持專業的醫療語調，並確保翻譯準確且易於理解：

原文：
{english_content}

繁體中文翻譯："""
                            
                            translation_headers = {
                                "Authorization": f"Bearer {api_key}",
                                "Content-Type": "application/json",
                                "HTTP-Referer": os.getenv('APP_PUBLIC_URL', 'http://127.0.0.1'),
                                "X-Title": os.getenv('APP_TITLE', 'HoloWellness Translation')
                            }
                            
                            translation_data = {
                                "model": "deepseek/deepseek-r1-distill-qwen-14b",
                                "messages": [{"role": "user", "content": translation_prompt}],
                                "max_tokens": 500,
                                "temperature": 0.1
                            }
                            
                            translation_response = requests.post(
                                "https://openrouter.ai/api/v1/chat/completions",
                                headers=translation_headers,
                                json=translation_data,
                                timeout=30
                            )
                            
                            if translation_response.status_code == 200:
                                translation_result = translation_response.json()
                                translated_content = translation_result['choices'][0]['message']['content']
                            else:
                                logger.warning("Translation failed, using English content")
                                translated_content = english_content
                                
                    except Exception as translation_error:
                        logger.warning(f"Translation failed: {translation_error}, using English content")
                        translated_content = english_content
                    
                    # Create response_data structure for consistency with normal flow
                    response_data = {
                        "content": translated_content,
                        "thinking": thinking,
                        "retrieved_context": retrieved_context,
                        "reranked": False,
                        "num_sources": 0
                    }
                    
                    logger.info(f"✅ Fallback successful, content length: {len(translated_content)}")
                else:
                    logger.error(f"❌ OpenRouter API error: {response.status_code} - {response.text}")
                    raise Exception(f"OpenRouter API error: {response.status_code}")
                    
            except Exception as fallback_error:
                logger.error(f"❌ Fallback also failed: {fallback_error}")
                # Check if it's an OpenRouter/API error
                if hasattr(e, 'status_code') or 'api' in str(e).lower():
                    error_msg = f'LLM provider error: {str(e)[:400]}'
                    logger.error(f"🌐 API Error detected: {error_msg}")
                    return jsonify({'error': error_msg}), 502
                else:
                    error_msg = f'Chat generation failed: {str(e)}'
                    logger.error(f"💥 General error: {error_msg}")
                    return jsonify({'error': error_msg}), 500

        # Extract response content (needed for both normal and fallback paths)
        content = response_data.get("content", "")
        thinking = response_data.get("thinking", "")
        retrieved_context = response_data.get("retrieved_context", "")
        
        # Enhanced response information
        reranked = response_data.get("reranked", False)
        
        # Calculate num_sources from 'sources' list if present (common in RAG responses)
        if 'sources' in response_data and isinstance(response_data['sources'], list):
            num_sources = len(response_data['sources'])
        else:
            num_sources = response_data.get("num_sources", 0)

        logger.info(f"Generated response with {len(content)} characters. Reranked: {reranked}, Sources: {num_sources}")

        # Get message_id from AI message
        message_id = memory_manager.add_ai_message(session_id, content, user_id=user_id)

        response_json = {
            'response': content,
            'message_id': message_id,
            'session_id': session_id,
            'thinking': thinking,
            'retrieved_context': retrieved_context
        }
        
        # Add enhanced RAG metadata if available
        if USE_ENHANCED_RAG:
            response_json['rag_metadata'] = {
                'reranked': reranked,
                'num_sources': num_sources,
                'system_type': 'enhanced'
            }

        return jsonify(response_json)

    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
 

@app.route('/api/store-message', methods=['POST'])
def store_message():
    """
    Allows manual insertion of a single message into a chatbot session for testing.
    """
    data = request.get_json()
    try:
        session_id = data["session_id"]
        user_id = data["user_id"]
        message_body = data["message_body"]
        is_user = data["is_user"]
        previous_message = data.get("previous_message", None)

        # Always fetch chatbot_id from the session
        chat_session = (memory_manager.chatbot_collection.find_one({"_id": ObjectId(session_id)})
                        if memory_manager.mongodb_available else memory_manager._get_session_document(session_id))
        chatbot_id = chat_session["chatbot"]

        memory_manager._store_message_to_mongo(
            session_id=session_id,
            user_id=user_id,
            chatbot_id=chatbot_id,
            message_body=message_body,
            is_user=is_user,
            previous_message=previous_message
        )
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route('/api/interactions', methods=['GET'])
def get_interactions():
    """
    Returns a list of chatbot interactions or a specific one if session_id is given.
    """
    try:
        session_id = request.args.get('session_id')

        if session_id:
            doc = memory_manager.chatbot_collection.find_one({"_id": ObjectId(session_id)})
            if not doc:
                return jsonify({'error': 'Interaction not found'}), 404
            return dumps(doc), 200

        # Otherwise return latest 10 sessions
        interactions = memory_manager.chatbot_collection.find().sort("updated_at", -1).limit(10)
        return dumps(list(interactions)), 200

    except Exception as e:
        logger.error(f"Error in /api/interactions: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route("/api/chat/rate", methods=["POST"])
def rate_message():
    data = request.json
    message_id = data.get("message_id")
    rating = data.get("rating")

    if not message_id or rating is None:
        return jsonify({"error": "Missing message_id or rating"}), 400

    try:
        memory_manager.rate_message(message_id=message_id, rating=int(rating))
        return jsonify({"message": "Rating saved successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/memory', methods=['GET'])
def get_memory():
    """Get memory for a session"""
    session_id = request.args.get('session_id')
    if not session_id:
        return jsonify({'error': 'No session_id provided'}), 400
    
    history = memory_manager.get_chat_history(session_id)
    return jsonify({
        'session_id': session_id,
        'history': history
    })

@app.route('/api/memory/clear', methods=['POST'])
def clear_memory():
    """Clear memory for a session"""
    data = request.json
    if not data or 'session_id' not in data:
        return jsonify({'error': 'No session_id provided'}), 400
    
    session_id = data['session_id']
    memory_manager.clear_session(session_id)
    
    return jsonify({
        'status': 'ok',
        'message': f'Memory cleared for session {session_id}'
    })



@app.route('/api/rag/reindex', methods=['POST'])
def reindex_rag():
    try:
        sync_pdfs_from_s3()

        # Clear in-memory docs and indexes to avoid duplicates, then rebuild
        if hasattr(rag, 'documents'):
            rag.documents = []
        if hasattr(rag, 'vector_store'):
            rag.vector_store = None
        if hasattr(rag, 'bm25_index'):
            rag.bm25_index = None

        # Try downloading caches first; otherwise rebuild and upload
        if not try_download_caches(rag):
            rag._ingest_documents()
            rag._save_embeddings()
            try_upload_caches(rag)

        # Get all files currently in S3/local after sync
        local_files = {f for f in os.listdir(PDF_DIR) if f.lower().endswith('.pdf')}
        
        # Update status for each RAG file in the database
        for rag_file in memory_manager.ragfiles_collection.find({}):
            if rag_file.get("file_name") in local_files:
                memory_manager.ragfiles_collection.update_one(
                    {"_id": rag_file["_id"]},
                    {"$set": {
                        "ingestion_status": "success",
                        "ingestion_message": "Ingestion completed successfully.",
                        "date_modified": datetime.utcnow()
                    }}
                )
            else:
                memory_manager.ragfiles_collection.update_one(
                    {"_id": rag_file["_id"]},
                    {"$set": {
                        "ingestion_status": "missing",
                        "ingestion_message": "File not found in local PDFs folder.",
                        "date_modified": datetime.utcnow()
                    }}
                )

        return jsonify({
            'status': 'ok',
            'message': 'PDFs synced & RAG vectorstore rebuilt.',
            'documents_indexed': len(rag.documents) if rag and hasattr(rag, 'documents') else 0
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/rag/reindex-lambda', methods=['POST'])
def reindex_rag_lambda():
    """
    Lambda-based reindexing - offloads heavy processing to AWS Lambda
    Solves disk space issues on EC2 by processing in Lambda /tmp
    """
    try:
        # Check if Lambda indexing is enabled
        use_lambda = os.getenv('USE_LAMBDA_INDEXING', 'false').lower() == 'true'
        
        if not use_lambda:
            return jsonify({
                'status': 'error',
                'message': 'Lambda indexing not enabled. Set USE_LAMBDA_INDEXING=true'
            }), 400
            
        # Initialize Lambda client
        lambda_client = LambdaIndexingClient(
            function_name=os.getenv('LAMBDA_FUNCTION_NAME', 'holowellness-rag-indexer'),
            region=os.getenv('AWS_REGION', 'ap-northeast-3'),
            s3_bucket=RAG_S3_BUCKET,
            s3_cache_prefix=os.getenv('S3_CACHE_PREFIX', 'cache/current/')
        )
        
        logger.info("🚀 Starting Lambda-based reindexing...")
        
        # Trigger Lambda indexing with completion monitoring
        result = lambda_client.reindex_and_update(timeout_seconds=600)
        
        if result['success']:
            # Clear local RAG state to force reload from fresh S3 cache
            if hasattr(rag, 'documents'):
                rag.documents = []
            if hasattr(rag, 'vector_store'):
                rag.vector_store = None
            if hasattr(rag, 'bm25_index'):
                rag.bm25_index = None

            # Force reload from the fresh S3 cache and load into memory
            if try_download_caches(rag):
                rag._load_or_create_embeddings()
            
            # Update database status
            try:
                for rag_file in memory_manager.ragfiles_collection.find({}):
                    memory_manager.ragfiles_collection.update_one(
                        {"_id": rag_file["_id"]},
                        {"$set": {
                            "ingestion_status": "success",
                            "ingestion_message": "Lambda indexing completed successfully.",
                            "date_modified": datetime.utcnow()
                        }}
                    )
            except Exception as db_error:
                logger.warning(f"Database update failed: {db_error}")
            
            return jsonify({
                'status': 'ok',
                'message': 'Lambda indexing completed successfully',
                'method': 'lambda',
                'job_id': result['job_id'],
                'processing_time': result['processing_time'],
                'documents_processed': result.get('documents_processed', 0),
                'cache_size_mb': result.get('cache_size_mb', 0),
                'documents_indexed': len(rag.documents) if rag and hasattr(rag, 'documents') else 0
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f"Lambda indexing failed: {result.get('error', 'Unknown error')}",
                'method': 'lambda',
                'job_id': result.get('job_id'),
                'details': result
            }), 500
            
    except Exception as e:
        logger.error(f"Lambda reindex error: {str(e)}")
        return jsonify({
            'status': 'error', 
            'message': f'Lambda indexing error: {str(e)}',
            'method': 'lambda'
        }), 500


@app.route('/api/rag/status', methods=['GET'])
def rag_status():
    try:
        local_dir = PDF_DIR
        files = []
        if os.path.isdir(local_dir):
            files = [f for f in os.listdir(local_dir) if f.lower().endswith('.pdf')]
        cache_dir = os.path.join(os.path.dirname(__file__), 'cache')
        cache_files = {}
        for name in ('vector_index.faiss', 'documents.pkl', 'documents.pkl.gz', 'bm25_index.pkl'):
            path = os.path.join(cache_dir, name)
            cache_files[name] = os.path.getsize(path) if os.path.exists(path) else None
        # S3 cache info
        s3_info = {
            'bucket': os.getenv('S3_CACHE_BUCKET') or RAG_S3_BUCKET,
            'prefix': os.getenv('S3_CACHE_PREFIX', 'cache/current/')
        }

        return jsonify({
            'bucket': RAG_S3_BUCKET,
            'prefix': RAG_S3_PREFIX,
            'local_pdfs_count': len(files),
            'local_pdfs': files,
            'documents_indexed': len(rag.documents) if rag and hasattr(rag, 'documents') else 0,
            'cache_files': cache_files,
            's3_cache': s3_info
        })
    except Exception as e:
        logger.error(f"/api/rag/status error: {e}")
        return jsonify({'error': str(e)}), 500



@app.route('/api/health', methods=['GET'])
def api_health_check():
    return jsonify({'status': 'ok', 'message': 'RAG system is running'})

@app.route('/api/debug/routes', methods=['GET'])
def debug_routes():
    """Debug endpoint to list all available routes"""
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': list(rule.methods),
            'rule': str(rule)
        })
    return jsonify({'routes': routes})

@app.route('/minimal', methods=['GET'])
def minimal():
    """Serve the minimal HTML test file"""
    return send_from_directory('static', 'minimal.html')

@app.route('/assets/<path:filename>')
def serve_assets(filename):
    """Serve Vite build assets (JS, CSS, etc.)"""
    return send_from_directory('static/assets', filename)

@app.route('/<path:filename>')
def serve_static_files(filename):
    """Serve other static files from the static directory"""
    try:
        return send_from_directory('static', filename)
    except FileNotFoundError:
        # If file not found, serve index.html for SPA routing
        return send_from_directory('static', 'index.html')



if __name__ == '__main__':
    logger.info("Starting Flask server on port 5000")
    app.run(host='0.0.0.0', port=5000, debug=True) 