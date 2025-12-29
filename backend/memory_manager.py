from langchain.memory import (
    ConversationBufferMemory,
    ConversationBufferWindowMemory,
    ConversationTokenBufferMemory,
    ConversationSummaryMemory,
)
from langchain.schema import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
import os
from typing import Dict, List, Any, Optional
import time
import threading
import logging
from pymongo import MongoClient
from bson import ObjectId
import uuid
from datetime import datetime
import os
import threading
from pymongo import MongoClient
from dotenv import load_dotenv
from bson import ObjectId, errors
from langchain_core.language_models import BaseChatModel
from langchain_core.language_models import BaseLanguageModel  # for token counting interface
import tiktoken

# Vector store & embedding
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

load_dotenv()  # Load environment variables from .env


logger = logging.getLogger(__name__)

class TokenCountingLLM(BaseLanguageModel):
    """A minimal LLM that only implements token counting for LangChain memory.
    It never actually generates text – it's used solely so ConversationTokenBufferMemory
    can call `get_num_tokens_(from_)messages` without requiring an external API key."""

    enc: Any = None
    model_name: str = "gpt2"

    def __init__(self, model_name: str = "gpt2", **kwargs):
        super().__init__(**kwargs)
        object.__setattr__(self, 'enc', tiktoken.get_encoding(model_name))
        object.__setattr__(self, 'model_name', model_name)

    @property
    def _llm_type(self) -> str:
        return "token-count-only"

    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:  # type: ignore[override]
        raise NotImplementedError("TokenCountingLLM is for counting only, not generation")

    # Token counting helpers used by LangChain memory
    def get_num_tokens(self, text: str) -> int:  # type: ignore
        return len(self.enc.encode(text))

    def get_num_tokens_from_messages(self, messages: List[Any]) -> int:  # type: ignore
        total = 0
        for m in messages:
            if hasattr(m, "content") and isinstance(m.content, str):
                total += self.get_num_tokens(m.content)
        return total

    # Required abstract methods from BaseLanguageModel
    def generate_prompt(self, prompts, stop=None, callbacks=None, **kwargs):
        raise NotImplementedError("TokenCountingLLM is for counting only, not generation")
    
    def agenerate_prompt(self, prompts, stop=None, callbacks=None, **kwargs):
        raise NotImplementedError("TokenCountingLLM is for counting only, not generation")
    
    def predict(self, text, stop=None, **kwargs):
        raise NotImplementedError("TokenCountingLLM is for counting only, not generation")
    
    def apredict(self, text, stop=None, **kwargs):
        raise NotImplementedError("TokenCountingLLM is for counting only, not generation")
    
    def predict_messages(self, messages, stop=None, **kwargs):
        raise NotImplementedError("TokenCountingLLM is for counting only, not generation")
    
    def apredict_messages(self, messages, stop=None, **kwargs):
        raise NotImplementedError("TokenCountingLLM is for counting only, not generation")
    
    def invoke(self, input, config=None, **kwargs):
        raise NotImplementedError("TokenCountingLLM is for counting only, not generation")

class HybridMemory:
    """Custom memory that combines token buffer with rolling summarization."""
    
    def __init__(self, llm, max_token_limit: int = 6000):
        self.token_memory = ConversationTokenBufferMemory(
            llm=llm, 
            max_token_limit=max_token_limit, 
            return_messages=True
        )
        self.summary = ""  # Rolling summary of older conversations
        self.llm = llm
        
    def add_user_message(self, message: str):
        # Before adding, check if we need to summarize old content
        self._maybe_summarize()
        self.token_memory.chat_memory.add_user_message(message)
        
    def add_ai_message(self, message: str):
        self.token_memory.chat_memory.add_ai_message(message)
        
    def _maybe_summarize(self):
        """Summarize older messages if token buffer is getting full."""
        current_messages = self.token_memory.chat_memory.messages
        if len(current_messages) > 10:  # If we have many messages, summarize older ones
            # Take first 6 messages for summarization
            old_messages = current_messages[:6]
            recent_messages = current_messages[6:]
            
            # Create summary of old messages
            conversation_text = "\n".join([
                f"{'User' if isinstance(msg, HumanMessage) else 'Assistant'}: {msg.content}"
                for msg in old_messages
            ])
            
            try:
                if hasattr(self.llm, '_call'):  # Real LLM
                    summary_prompt = f"Summarize this medical conversation concisely:\n{conversation_text}\n\nSummary:"
                    new_summary = self.llm._call(summary_prompt)
                    if self.summary:
                        self.summary = f"{self.summary}\n{new_summary}"
                    else:
                        self.summary = new_summary
            except:
                # Fallback: simple concatenation for TokenCountingLLM
                self.summary = f"{self.summary}\nOlder conversation: {len(old_messages)} messages"
            
            # Keep only recent messages in token buffer
            self.token_memory.chat_memory.messages = recent_messages
            
    @property
    def messages(self):
        """Return messages with summary prepended if available."""
        messages = []
        if self.summary:
            messages.append(HumanMessage(content=f"Previous conversation summary: {self.summary}"))
        messages.extend(self.token_memory.chat_memory.messages)
        return messages

class MemoryManager:
    """Manages conversation memory using LangChain memory components"""
    
    def __init__(self, memory_type: str = "buffer_window", max_token_limit: int = 2000):
        """
        Initialize the memory manager
        
        Args:
            memory_type: Type of memory to use (buffer, buffer_window, token_buffer, summary)
            max_token_limit: Maximum number of tokens to store in memory
        """

        # MongoDB connection with fallback to in-memory storage
        mongo_uri = os.getenv("MONGO_URI")
        mongo_db_name = os.getenv("MONGO_DB_NAME", "db_holo_wellness")
        chatbot_coll_name = os.getenv("MONGO_CHAT_COLLECTION", "chatbotinteractions")
        ragfiles_coll_name = os.getenv("MONGO_RAGFILES_COLLECTION", "ragfiles")
        self.mongodb_available = False
        self.mongo_client = None
        self.mongo_db = None
        self.chatbot_collection = None
        self.ragfiles_collection = None
        
        # In-memory fallback storage
        self.in_memory_sessions = {}  # session_id -> session document
        self.in_memory_ragfiles = {}  # file_id -> ragfile document
        
        # Initialize memory configuration
        self.memory_type = memory_type
        self.max_token_limit = max_token_limit
        self.sessions = {}
        self.last_access = {}
        # In-memory session summaries (fallback when MongoDB is not configured)
        self.session_summaries: Dict[str, Dict[str, Any]] = {}
        
        # Initialize LLM for memory types that need it
        self.llm = None
        if memory_type in {"summary", "token_buffer"}:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self.llm = ChatOpenAI(api_key=api_key)
            else:
                self.llm = TokenCountingLLM()
        
        # Initialize Mongo if URI provided; else use in-memory fallback
        if mongo_uri:
            try:
                self.mongo_client = MongoClient(
                    mongo_uri,
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=5000,
                    maxPoolSize=int(os.getenv("MONGO_MAX_POOL_SIZE", "20")),
                    retryWrites=True
                )
                # Validate the connection
                self.mongo_client.admin.command('ping')
                self.mongo_db = self.mongo_client[mongo_db_name]
                self.chatbot_collection = self.mongo_db[chatbot_coll_name]
                self.ragfiles_collection = self.mongo_db[ragfiles_coll_name]
                # Dedicated collection for summaries (compact, one doc per session)
                self.session_summaries_collection = self.mongo_db.get_collection(
                    os.getenv("MONGO_SESSION_SUMMARY_COLLECTION", "session_summaries")
                )
                # Ensure indexes for performance and data access patterns
                self._ensure_indexes()
                self.mongodb_available = True
                logger.info(
                    "✅ MongoDB connected: db=%s, collections=[%s,%s]",
                    mongo_db_name,
                    chatbot_coll_name,
                    ragfiles_coll_name,
                )
            except Exception as e:
                logger.warning(
                    f"⚠️ MongoDB connection failed: {e}. Falling back to in-memory storage.",
                    exc_info=True,
                )
                self.mongodb_available = False
                self.mongo_client = None
        else:
            logger.info("🧠 No MONGO_URI provided. Using in-memory storage for session management.")
            self.session_summaries_collection = None

        self.memory_type = memory_type
        self.max_token_limit = max_token_limit
        self.sessions = {}
        self.last_access = {}
        # --- Long-term vector memory ---
        self.vector_stores = {}        # session_id -> faiss index
        self.fact_texts = {}           # session_id -> List[str]
        self.fact_embedder = SentenceTransformer("all-MiniLM-L6-v2")
        self.embedding_dim = self.fact_embedder.get_sentence_embedding_dimension()
        
        # Start cleanup thread
        self.cleanup_thread = threading.Thread(target=self._cleanup_old_sessions, daemon=True)
        self.cleanup_thread.start()

    def _ensure_indexes(self) -> None:
        """Create indexes used by the app. Safe to call repeatedly."""
        try:
            if self.chatbot_collection is not None:
                # Query latest sessions efficiently
                self.chatbot_collection.create_index([("updated_at", -1)])
                # Make message_id lookups faster for rating updates
                self.chatbot_collection.create_index("messages.message_id")
            if self.ragfiles_collection is not None:
                self.ragfiles_collection.create_index("file_name", unique=False)
            if getattr(self, 'session_summaries_collection', None) is not None:
                self.session_summaries_collection.create_index("session_id", unique=True)
        except Exception as e:
            logger.warning(f"Index creation failed: {e}")
    
    def _get_session_document(self, session_id: str):
        """Get session document from MongoDB or in-memory storage"""
        if self.mongodb_available:
            try:
                return self.chatbot_collection.find_one({"_id": ObjectId(session_id)})
            except Exception:
                # Invalid ObjectId string – treat as not found so caller can create a new session
                return None
        else:
            return self.in_memory_sessions.get(session_id)
    
    def _create_session_document(self, session_id: str, user_id: str, chatbot_id: str, title: str = "Default Chat Session"):
        """Create session document in MongoDB or in-memory storage"""
        from datetime import datetime
        now = datetime.utcnow()
        
        session_doc = {
            "_id": ObjectId(session_id) if self.mongodb_available else session_id,
            "chatbox_title": title,
            "user": ObjectId(user_id) if self.mongodb_available else user_id,
            "chatbot": ObjectId(chatbot_id) if self.mongodb_available else chatbot_id,
            "messages": [],
            "created_at": now,
            "updated_at": now
        }
        
        if self.mongodb_available:
            self.chatbot_collection.insert_one(session_doc)
        else:
            self.in_memory_sessions[session_id] = session_doc
            
        return session_doc
    
    def _update_session_document(self, session_id: str, update_data: dict):
        """Update session document in MongoDB or in-memory storage"""
        if self.mongodb_available:
            return self.chatbot_collection.update_one(
                {"_id": ObjectId(session_id)},
                {"$set": update_data}
            )
        else:
            if session_id in self.in_memory_sessions:
                self.in_memory_sessions[session_id].update(update_data)
                return type('MockResult', (), {'matched_count': 1})()
            return type('MockResult', (), {'matched_count': 0})()
    
    def _push_message_to_session(self, session_id: str, message_doc: dict):
        """Push message to session document in MongoDB or in-memory storage"""
        from datetime import datetime
        now = datetime.utcnow()
        
        if self.mongodb_available:
            return self.chatbot_collection.update_one(
                {"_id": ObjectId(session_id)},
                {
                    "$push": {"messages": message_doc},
                    "$set": {"updated_at": now}
                }
            )
        else:
            if session_id in self.in_memory_sessions:
                self.in_memory_sessions[session_id]["messages"].append(message_doc)
                self.in_memory_sessions[session_id]["updated_at"] = now
                return type('MockResult', (), {'matched_count': 1})()
            return type('MockResult', (), {'matched_count': 0})()
    
    def _create_memory(self) -> Any:
        """Create a new memory instance based on the configured type"""
        if self.memory_type == "buffer":
            return ConversationBufferMemory(return_messages=True)
        elif self.memory_type == "buffer_window":
            return ConversationBufferWindowMemory(k=5, return_messages=True)
        elif self.memory_type == "token_buffer":
            if self.llm is None:
                self.llm = TokenCountingLLM()  # Fallback if not initialized
            return HybridMemory(llm=self.llm, max_token_limit=self.max_token_limit)
        elif self.memory_type == "summary":
            if self.llm is None:
                self.llm = TokenCountingLLM()  # Fallback if not initialized
            return ConversationSummaryMemory(llm=self.llm, return_messages=True)
        else:
            # Default to buffer window memory
            return ConversationBufferWindowMemory(k=5, return_messages=True)
        

    
    def get_session(self, session_id: str) -> Any:
        """Get or create a memory session"""
        if session_id not in self.sessions:
            # Create a new working memory instance
            self.sessions[session_id] = self._create_memory()
            # If MongoDB persistence is enabled, hydrate working memory from stored messages
            if self.mongodb_available:
                try:
                    doc = self._get_session_document(session_id)
                    if doc and isinstance(doc.get("messages"), list):
                        memory = self.sessions[session_id]
                        for m in doc["messages"]:
                            body = m.get("message_body", "")
                            if not body:
                                continue
                            is_user = bool(m.get("direction", True))
                            # Support HybridMemory and standard LangChain memories
                            if hasattr(memory, 'add_user_message') and hasattr(memory, 'add_ai_message'):
                                if is_user:
                                    memory.add_user_message(body)
                                else:
                                    memory.add_ai_message(body)
                            else:
                                chat_mem = getattr(memory, 'chat_memory', None)
                                if chat_mem is not None:
                                    if is_user:
                                        chat_mem.add_user_message(body)
                                    else:
                                        chat_mem.add_ai_message(body)
                except Exception as e:
                    logger.warning(f"Hydration from MongoDB failed for session {session_id}: {e}")
        
        # Update last access time
        self.last_access[session_id] = time.time()
        return self.sessions[session_id]
    
  


    def _store_message_to_mongo(self, session_id: str, user_id: str, chatbot_id: str,
                            message_body: str, is_user: bool, previous_message: str = None):
        """
        Appends a message to an EXISTING session document in MongoDB or in-memory storage.
        Does NOT create a new document if session not found.
        """
        # Validate session_id format for MongoDB if needed
        if self.mongodb_available:
            try:
                ObjectId(session_id)
            except (errors.InvalidId, TypeError):
                raise ValueError(f"Invalid session_id: {session_id}")

        now = datetime.utcnow()

        # Prepare the message document
        message_doc = {
            "message_id": str(uuid.uuid4()),
            "chatbot": ObjectId(chatbot_id) if self.mongodb_available else chatbot_id,
            "message_body": message_body,
            "direction": is_user,
            "previous_message": previous_message,
            "created_at": now,
            "updated_at": now
        }

        # Store the message using helper method
        result = self._push_message_to_session(session_id, message_doc)
        if result.matched_count == 0:
            raise ValueError(f"No session document found for session_id {session_id}. Message not stored.")
        
    def add_user_message(self, session_id, message, user_id=None):
        memory = self.get_session(session_id)
        if hasattr(memory, 'add_user_message'):
            memory.add_user_message(message)  # HybridMemory
        else:
            memory.chat_memory.add_user_message(message)  # Standard LangChain memory
        # Try to persist potential long-term fact
        self._maybe_store_long_term_fact(session_id, message)
        # Update deterministic answered slots for persistent summary
        try:
            self.update_answered_slots(session_id, message)
        except Exception as e:
            logger.warning(f"Failed to update answered slots: {e}")
        if user_id:
            # Fetch the chatbot_id from the session doc (should already exist!)
            session = self._get_session_document(session_id)
            if not session:
                raise ValueError(f"No session found for id {session_id}")
            chatbot_id = session["chatbot"]
            self._store_message_to_mongo(session_id, user_id, chatbot_id, message, is_user=True)

    def add_ai_message(self, session_id, message, user_id=None, previous_message=None):
        memory = self.get_session(session_id)
        if hasattr(memory, 'add_ai_message'):
            memory.add_ai_message(message)  # HybridMemory
        else:
            memory.chat_memory.add_ai_message(message)  # Standard LangChain memory
        message_id = None
        if user_id:
            session = self._get_session_document(session_id)
            chatbot_id = session["chatbot"]
            # -- Build message_doc here so you can get the UUID! --
            import uuid
            now = datetime.utcnow()
            message_doc = {
                "message_id": str(uuid.uuid4()),
                "chatbot": chatbot_id,
                "message_body": message,
                "direction": False,
                "previous_message": previous_message,
                "created_at": now,
                "updated_at": now
            }
            self._push_message_to_session(session_id, message_doc)
            message_id = message_doc["message_id"]
        return message_id


    def rate_message(self, message_id: str, rating: int) -> None:
        """
        Assigns a rating to a specific message in a chatbot interaction.
        Args:
            message_id: The UUID string of the message inside the messages array.
            rating: Integer rating (e.g., 1–5).
        """
        from datetime import datetime

        result = self.chatbot_collection.update_one(
            {"messages.message_id": message_id},
            {
                "$set": {
                    "messages.$.rating": rating,
                    "messages.$.rated_at": datetime.utcnow()
                }
            }
        )

        if result.matched_count == 0:
            raise ValueError(f"Message with ID {message_id} not found.")


    def get_chat_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get the chat history for a session"""
        if session_id not in self.sessions:
            return []
        
        memory = self.sessions[session_id]
        if hasattr(memory, 'messages'):
            messages = memory.messages  # HybridMemory
        else:
            messages = memory.chat_memory.messages  # Standard LangChain memory
        
        # Convert LangChain messages to dict format
        history = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                history.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                history.append({"role": "assistant", "content": msg.content})
        
        return history
    
    def get_memory_variables(self, session_id: str) -> Dict[str, Any]:
        """Get memory variables for a session"""
        memory = self.get_session(session_id)
        if hasattr(memory, 'load_memory_variables'):
            return memory.load_memory_variables({})  # Standard LangChain memory
        else:
            # For HybridMemory, return a summary of the current state
            return {
                "history": self.get_chat_history(session_id),
                "summary": getattr(memory, 'summary', ''),
                "message_count": len(memory.messages) if hasattr(memory, 'messages') else 0
            }
    
    def clear_session(self, session_id: str) -> None:
        """Clear a session from memory"""
        if session_id in self.sessions:
            del self.sessions[session_id]
        if session_id in self.last_access:
            del self.last_access[session_id]
    
    def _cleanup_old_sessions(self) -> None:
        """Periodically clean up old sessions to prevent memory leaks"""
        while True:
            try:
                current_time = time.time()
                session_timeout = 3600  # 1 hour in seconds
                
                # Find expired sessions
                expired_sessions = []
                for session_id, last_access in self.last_access.items():
                    if current_time - last_access > session_timeout:
                        expired_sessions.append(session_id)
                
                # Remove expired sessions
                for session_id in expired_sessions:
                    logger.info(f"Removing expired session: {session_id}")
                    self.clear_session(session_id)
                
                # If we have too many sessions, remove the oldest ones
                max_sessions = 100
                if len(self.sessions) > max_sessions:
                    # Sort sessions by last access time
                    sorted_sessions = sorted(
                        self.last_access.items(),
                        key=lambda x: x[1]
                    )
                    
                    # Remove oldest sessions
                    for session_id, _ in sorted_sessions[:len(self.sessions) - max_sessions]:
                        logger.info(f"Removing old session due to limit: {session_id}")
                        self.clear_session(session_id)
            
            except Exception as e:
                logger.error(f"Error in session cleanup: {e}")
            
            # Sleep for 10 minutes
            time.sleep(600)

    # ---------------- Long-term memory helpers ----------------

    def _maybe_store_long_term_fact(self, session_id: str, message: str):
        """Heuristic extraction & storage of personal facts into FAISS vector store."""
        text = message.strip()
        # Simple heuristic: if the user talks about themselves and the sentence is short
        if len(text) > 250:
            return  # skip long paragraphs for now
        lowered = text.lower()
        if not any(pron in lowered for pron in ["i ", "my ", "i'm", "i am", "me "]):
            return  # not obviously personal

        embedding = self.fact_embedder.encode([text])[0].astype(np.float32)

        # Create vector store for session if missing
        if session_id not in self.vector_stores:
            index = faiss.IndexFlatL2(self.embedding_dim)
            self.vector_stores[session_id] = index
            self.fact_texts[session_id] = []

        index = self.vector_stores[session_id]
        index.add(np.array([embedding]))
        self.fact_texts[session_id].append(text)

    def retrieve_long_term_memory(self, session_id: str, query: str, k: int = 3) -> List[str]:
        """Return top-k remembered facts for this session."""
        if session_id not in self.vector_stores or self.vector_stores[session_id].ntotal == 0:
            return []

        embedding = self.fact_embedder.encode([query])[0].astype(np.float32)
        D, I = self.vector_stores[session_id].search(np.array([embedding]), k)
        facts = []
        for idx in I[0]:
            if idx < len(self.fact_texts[session_id]):
                facts.append(self.fact_texts[session_id][idx])
        return facts

    # ---------------- Session summary and slot extraction ----------------

    _REQUIRED_MSK_SLOTS = [
        "onset", "location", "severity", "aggravating_factors", "relieving_factors",
        "swelling", "clicking", "locking", "functional_impact", "medications", "red_flags"
    ]

    def _extract_slots_from_text(self, text: str) -> Dict[str, Any]:
        """Heuristic extraction for common MSK slots from user text."""
        out: Dict[str, Any] = {}
        lowered = (text or "").lower()

        # Severity 0-10
        import re as _re
        sev = None
        m = _re.search(r"\b(\d{1,2})\s*/\s*10\b", lowered)
        if m:
            try:
                sev = int(m.group(1))
            except Exception:
                sev = None
        if sev is None:
            m2 = _re.search(r"\b(severity|pain)\s*(is|=)?\s*(\d{1,2})\b", lowered)
            if m2:
                try:
                    sev = int(m2.group(3))
                except Exception:
                    sev = None
        if sev is not None and 0 <= sev <= 10:
            out["severity"] = sev

        # Location keywords
        if any(k in lowered for k in ["front", "anterior"]):
            out["location"] = "front"
        elif any(k in lowered for k in ["back", "posterior"]):
            out["location"] = "back"
        elif any(k in lowered for k in ["inside", "medial", "inner"]):
            out["location"] = "medial"
        elif any(k in lowered for k in ["outside", "lateral", "outer"]):
            out["location"] = "lateral"

        # Onset
        if any(k in lowered for k in ["yesterday", "last night", "last week", "today", "this morning", "this evening"]):
            out["onset"] = next(k for k in ["yesterday", "last night", "last week", "today", "this morning", "this evening"] if k in lowered)

        # Swelling / clicking / locking
        if "swelling" in lowered or "swollen" in lowered:
            out["swelling"] = True
        if "clicking" in lowered or "popping" in lowered:
            out["clicking"] = True
        if "locking" in lowered or "locks" in lowered:
            out["locking"] = True

        # Aggravating / relieving
        if any(k in lowered for k in ["worse with", "worsens with", "aggravated by", "activity", "stairs", "running", "jumping"]):
            out.setdefault("aggravating_factors", [])
            for token in ["activity", "stairs", "running", "jumping"]:
                if token in lowered and token not in out["aggravating_factors"]:
                    out["aggravating_factors"].append(token)
        if any(k in lowered for k in ["better with", "relieved by", "rest", "ice", "ibuprofen", "medication"]):
            out.setdefault("relieving_factors", [])
            for token in ["rest", "ice", "ibuprofen", "medication"]:
                if token in lowered and token not in out["relieving_factors"]:
                    out["relieving_factors"].append(token)

        # Functional impact
        if any(k in lowered for k in ["can't bear weight", "cannot bear weight", "limp", "limping", "difficulty walking", "limited range"]):
            out["functional_impact"] = "weight-bearing difficulty" if ("bear weight" in lowered) else "mobility limitation"

        # Medications (simple)
        if any(k in lowered for k in ["ibuprofen", "acetaminophen", "naproxen"]):
            out.setdefault("medications", [])
            for token in ["ibuprofen", "acetaminophen", "naproxen"]:
                if token in lowered and token not in out["medications"]:
                    out["medications"].append(token)

        # Red flags (simple heuristic)
        if any(k in lowered for k in ["fever", "redness spreading", "numbness", "weakness", "deformity", "trauma"]):
            out.setdefault("red_flags", [])
            for token in ["fever", "redness spreading", "numbness", "weakness", "deformity", "trauma"]:
                if token in lowered and token not in out["red_flags"]:
                    out["red_flags"].append(token)

        return out

    def _load_session_summary(self, session_id: str) -> Dict[str, Any]:
        if self.mongodb_available and self.session_summaries_collection is not None:
            doc = self.session_summaries_collection.find_one({"session_id": session_id})
            if doc:
                return {
                    "answered_slots": doc.get("answered_slots", {}),
                    "unanswered_slots": doc.get("unanswered_slots", []),
                    "profile": doc.get("profile", {}),
                    "active_complaint": doc.get("active_complaint", {}),
                    "red_flags": doc.get("red_flags", []),
                    "updated_at": doc.get("updated_at")
                }
        return self.session_summaries.get(session_id, {
            "answered_slots": {},
            "unanswered_slots": self._REQUIRED_MSK_SLOTS.copy(),
            "profile": {},
            "active_complaint": {},
            "red_flags": []
        })

    def _save_session_summary(self, session_id: str, summary: Dict[str, Any]) -> None:
        summary = dict(summary)
        summary["session_id"] = session_id
        summary["updated_at"] = datetime.utcnow()
        if self.mongodb_available and self.session_summaries_collection is not None:
            self.session_summaries_collection.update_one(
                {"session_id": session_id},
                {"$set": summary},
                upsert=True
            )
        else:
            self.session_summaries[session_id] = summary

    def update_answered_slots(self, session_id: str, user_text: str) -> None:
        summary = self._load_session_summary(session_id)
        slots = self._extract_slots_from_text(user_text)
        if not slots:
            return
        answered = summary.get("answered_slots", {})
        answered.update(slots)
        summary["answered_slots"] = answered
        # Compute unanswered as required minus present keys
        required = set(self._REQUIRED_MSK_SLOTS)
        present = set([k for k, v in answered.items() if v not in (None, [], "")])
        summary["unanswered_slots"] = [s for s in self._REQUIRED_MSK_SLOTS if s not in present]
        # Merge red flags if present
        if "red_flags" in slots:
            rf = set(summary.get("red_flags", [])) | set(slots.get("red_flags", []))
            summary["red_flags"] = sorted(list(rf))
        self._save_session_summary(session_id, summary)

    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        return self._load_session_summary(session_id)

    def get_pinned_summary(self, session_id: str) -> str:
        """Return a compact, deterministic string to pin in prompts."""
        summary = self._load_session_summary(session_id)
        answered = summary.get("answered_slots", {})
        unanswered = summary.get("unanswered_slots", [])
        red_flags = summary.get("red_flags", [])
        parts: List[str] = []
        if answered:
            # Compact key: value list, keep it under control
            kv = []
            for k in [
                "onset","location","severity","swelling","clicking","locking",
                "aggravating_factors","relieving_factors","functional_impact","medications"
            ]:
                if k in answered and answered[k] not in (None, [],""):
                    kv.append(f"{k}={answered[k]}")
            if kv:
                parts.append("AnsweredSlots: " + "; ".join(kv))
        if unanswered:
            parts.append("UnansweredSlots: " + ", ".join(unanswered[:4]))  # keep short
        if red_flags:
            parts.append("RedFlags: " + ", ".join(red_flags))
        return "\n".join(parts)

# Create a global instance with default settings
memory_manager = MemoryManager(memory_type="token_buffer", max_token_limit=6000) 