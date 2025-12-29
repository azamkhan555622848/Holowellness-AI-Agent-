# 🏥 HoloWellness AI Agent v2.0 (DeepAgents Edition)

> **A multimodal clinical wellness chatbot powered by DeepAgents middleware, Google Gemma 3 27B, and persistent agent memory**

[![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)](https://github.com/azamkhan555622848/Holowellness-AI-Agent-)
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9+-green.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/react-18.3.1-61DAFB.svg)](https://reactjs.org/)

---

## 📋 Table of Contents

- [What's New in v2.0](#-whats-new-in-v20-deepagents-edition)
- [Architecture Overview](#-architecture-overview)
- [Key Differences: v1.0 vs v2.0](#-key-differences-v10-vs-v20)
- [Project Structure](#-project-structure)
- [How It Works](#-how-the-ai-agent-works)
- [Backend Components](#-backend-components-deep-dive)
- [Frontend Components](#-frontend-components)
- [Database Schema](#-database-schema-mongodb-atlas)
- [Setup & Installation](#-setup--installation)
- [Configuration](#-configuration)
- [API Documentation](#-api-documentation)
- [Development Workflow](#-development-workflow)
- [Testing](#-testing)
- [Deployment](#-deployment)
- [Migration Guide](#-migration-guide-from-v10-to-v20)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)

---

## 🆕 What's New in v2.0 (DeepAgents Edition)

### Revolutionary Features

1. **🧠 Agent-Based Architecture**
   - Built on [DeepAgents](https://github.com/deepagents/deepagents) middleware framework
   - Agent has access to **virtual filesystem** for memory management
   - Persistent memory across sessions via MongoDB

2. **📁 Virtual Filesystem (VFS)**
   - Agent can `ls`, `read_file`, `write_file`, and `edit_file`
   - `/memories/` directory persisted permanently in MongoDB
   - Patient profiles, workout history, and exercise library accessible as files

3. **🔧 Advanced Tool System**
   - `search_guidelines_tool` - RAG search through clinical PDFs
   - File manipulation tools for patient data management
   - Built-in todo list middleware for agent planning

4. **🖼️ Native Multimodal Support**
   - Gemma 3 27B can analyze images (workout logs, food photos, symptoms)
   - Base64 image upload via frontend
   - Vision capabilities built into agent system prompt

5. **🔐 Enhanced Authentication**
   - JWT-based auth with bcrypt password hashing
   - Optional anonymous chat mode
   - Platform integration for external auth providers

6. **📊 Patient Context Management**
   - Agent automatically checks `/memories/patient_profile.json`
   - Workout history tracking in `/memories/recent_workouts.json`
   - Exercise library catalog in `/memories/exercise_library.json`

---

## 🏗️ Architecture Overview

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (React + Vite)                         │
│  ┌────────────────┐    ┌──────────────┐    ┌────────────────────────────┐  │
│  │  ChatContainer │───▶│  useChat()   │───▶│  POST /api/chat            │  │
│  │  + Image Upload│    │  hook        │    │  { query, image_base64 }   │  │
│  └────────────────┘    └──────────────┘    └────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              BACKEND (Flask API)                             │
│  ┌─────────────┐    ┌──────────────┐    ┌────────────────────────────────┐  │
│  │  app.py     │───▶│ agentic_     │───▶│  agent_factory.py              │  │
│  │  /api/chat  │    │ chat()       │    │  create_holowellness_agent()   │  │
│  └─────────────┘    └──────────────┘    └────────────────────────────────┘  │
│                                                        │                      │
│                                                        ▼                      │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                    DEEPAGENTS MIDDLEWARE LAYER                          │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐   │  │
│  │  │ Filesystem      │  │ TodoList        │  │ Summarization       │   │  │
│  │  │ Middleware      │  │ Middleware      │  │ Middleware          │   │  │
│  │  │ (ls, read,      │  │ (write_todos)   │  │ (context window)    │   │  │
│  │  │  write, edit)   │  │                 │  │                     │   │  │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────┘   │  │
│  │                                                                         │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │              COMPOSITE BACKEND (Memory Management)               │  │  │
│  │  │  ┌──────────────────┐         ┌─────────────────────────────┐  │  │  │
│  │  │  │ /memories/       │────────▶│  StoreBackend               │  │  │  │
│  │  │  │ (Persistent)     │         │  → DeepAgentsMongoStore     │  │  │  │
│  │  │  └──────────────────┘         └─────────────────────────────┘  │  │  │
│  │  │  ┌──────────────────┐         ┌─────────────────────────────┐  │  │  │
│  │  │  │ Other paths      │────────▶│  StateBackend               │  │  │  │
│  │  │  │ (Ephemeral)      │         │  → In-memory (per session)  │  │  │  │
│  │  │  └──────────────────┘         └─────────────────────────────┘  │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                        │                                      │
│                                        ▼                                      │
│  ┌────────────────────┐    ┌─────────────────────┐    ┌──────────────────┐  │
│  │ OpenRouter API     │    │ RAG System          │    │ MongoDB Atlas    │  │
│  │ (Gemma 3 27B)      │    │ (FAISS + BM25)      │    │ - Users          │  │
│  │ - Vision           │    │ - Clinical PDFs     │    │ - Profiles       │  │
│  │ - Reasoning        │    │ - Reranking         │    │ - Workouts       │  │
│  └────────────────────┘    └─────────────────────┘    │ - agent_store    │  │
│                                                         └──────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Architectural Principles

1. **Agent-First Design**: The AI is not just an LLM endpoint—it's an autonomous agent with tools
2. **Persistent Memory**: Agent memory survives server restarts via MongoDB
3. **Separation of Concerns**:
   - Frontend → User interaction
   - Backend API → Request handling
   - Agent Factory → Agent instantiation
   - DeepAgents → Middleware & tool execution
   - MongoDB → Persistent storage

---

## 🔄 Key Differences: v1.0 vs v2.0

### v1.0 (Legacy/Older Version)

| Component | v1.0 Architecture |
|-----------|-------------------|
| **Framework** | Direct LLM calls via OpenRouter |
| **Model** | DeepSeek R1 Distill Qwen 14B / GPT-OSS-120B |
| **Memory** | Session-based conversation history only |
| **Tools** | RAG search only |
| **Patient Data** | MongoDB queries in backend code |
| **Context** | Limited to recent conversation |
| **Multimodal** | Manual image encoding + prompt injection |
| **Agent State** | Stateless (no memory between restarts) |
| **Code Structure** | Monolithic `app.py` with direct RAG calls |

### v2.0 (DeepAgents Edition) ✨

| Component | v2.0 Architecture |
|-----------|-------------------|
| **Framework** | **DeepAgents middleware** with LangChain |
| **Model** | **Google Gemma 3 27B** (multimodal) |
| **Memory** | **Persistent virtual filesystem** in MongoDB |
| **Tools** | File system tools + RAG + TodoList middleware |
| **Patient Data** | **Agent reads from virtual files** (`/memories/*.json`) |
| **Context** | Agent can access historical data across sessions |
| **Multimodal** | **Native vision support** via `HumanMessage` |
| **Agent State** | **Persistent state** (survives server restarts) |
| **Code Structure** | **Modular**: Agent Factory + Tools + Store |

### Migration Impact

```diff
// v1.0: Direct MongoDB query in endpoint
- profile = memory_manager.get_patient_profile(user_id)
- response = rag.generate_answer(query, profile)

// v2.0: Agent autonomously reads from virtual filesystem
+ agent = create_holowellness_agent(session_id, user_id, rag)
+ result = agent.invoke(messages=[HumanMessage(content=query)])
+ # Agent internally calls: read_file("/memories/patient_profile.json")
```

**Why This Matters:**
- ✅ Agent decides WHEN to read patient data (only if relevant)
- ✅ Agent can UPDATE patient data based on conversation
- ✅ Memory persists even if server crashes
- ✅ Easier to add new tools without modifying core logic

---

## 📁 Project Structure

```
Holowellness_Chatbot_version_1.0/
│
├── backend/                       # ⚙️ Python/Flask Backend (DeepAgents)
│   ├── app.py                     # Main Flask server & API routes
│   ├── agent_factory.py           # ★ Agent creation with DeepAgents
│   ├── agent_store.py             # ★ MongoDB virtual filesystem store
│   ├── agent_tools.py             # ★ Custom tools (RAG search)
│   ├── auth.py                    # JWT authentication manager
│   ├── memory_manager.py          # MongoDB data access layer
│   ├── platform_client.py         # External platform integration
│   ├── enhanced_rag_qwen.py       # RAG with FAISS + BM25 + Reranking
│   ├── rag_qwen.py                # Basic RAG system (fallback)
│   ├── openrouter_client.py       # OpenRouter API wrapper
│   ├── sync_rag_pdfs.py           # S3 PDF sync utility
│   ├── s3_cache.py                # S3 cache manager for embeddings
│   ├── lambda_client.py           # AWS Lambda integration
│   ├── requirements.txt           # Python dependencies
│   ├── .env                       # Environment variables (local)
│   ├── pdfs/                      # Clinical guideline PDFs
│   └── static/                    # Built frontend assets
│
├── src/                           # 🎨 React/Vite Frontend (TypeScript)
│   ├── components/
│   │   ├── chat/                  # Chat UI components
│   │   │   ├── ChatContainer.tsx  # Main chat interface
│   │   │   ├── ChatInput.tsx      # Text + Image input
│   │   │   ├── ChatMessage.tsx    # Message rendering
│   │   │   ├── ChatSidebar.tsx    # Conversation history
│   │   │   ├── ThinkingIndicator.tsx
│   │   │   └── WelcomeScreen.tsx
│   │   └── ui/                    # shadcn/ui components
│   ├── hooks/
│   │   ├── useChat.ts             # ★ Chat API logic
│   │   ├── useAuth.tsx            # Authentication state
│   │   └── useTheme.ts            # Dark mode
│   ├── pages/
│   │   ├── Index.tsx              # Main chat page
│   │   └── NotFound.tsx
│   ├── types/
│   │   └── chat.ts                # TypeScript interfaces
│   ├── App.tsx                    # Main React component
│   └── main.tsx                   # React entry point
│
├── services/                      # 🔧 Microservices (Optional)
│   └── gemma-rag-service/         # Standalone Gemma RAG service
│       ├── app/main.py
│       ├── rag/sqlite_engine.py
│       └── rag/openrouter_client.py
│
├── lambda/                        # ☁️ AWS Lambda Functions
│   ├── rag_indexer.py             # Lambda-based RAG indexing
│   ├── build_package.sh
│   └── deploy.sh
│
├── deploy/                        # 🚀 Deployment Scripts
│   ├── aws-setup.sh
│   └── deploy-app.sh
│
├── .github/workflows/             # CI/CD Pipelines
│   └── deploy.yml
│
├── package.json                   # Node.js dependencies
├── vite.config.ts                 # Vite dev server config
├── tsconfig.json                  # TypeScript config
├── tailwind.config.ts             # Tailwind CSS config
├── gunicorn.conf.py               # Gunicorn production config
├── README.md                      # This file
├── ARCHITECTURE.md                # Detailed architecture docs
└── HOW_IT_WORKS.md                # Flow diagrams

★ = DeepAgents v2.0 specific files
```

---

## 🧠 How the AI Agent Works

### End-to-End Request Flow

```
1. USER sends message:
   "My knee hurts when climbing stairs. I'm 35 years old."

2. FRONTEND (useChat.ts):
   POST /api/chat
   {
     query: "My knee hurts...",
     session_id: "abc123",
     user_id: "507f1f77bcf86cd799439011"
   }

3. BACKEND (app.py):
   - Validates JWT token
   - Calls agentic_chat(query, user_id, session_id)

4. AGENT FACTORY (agent_factory.py):
   - Creates DeepAgents agent with:
     ✓ LLM: ChatOpenAI → OpenRouter → Gemma 3 27B
     ✓ Backend: CompositeBackend
       - /memories/ → StoreBackend → MongoDB
       - other paths → StateBackend → RAM
     ✓ Store: DeepAgentsMongoStore
     ✓ Tools: [search_guidelines_tool, ls, read_file, write_file, edit_file]

   - Seeds virtual filesystem if empty:
     ✓ /memories/patient_profile.json
     ✓ /memories/recent_workouts.json
     ✓ /memories/exercise_library.json

5. AGENT EXECUTION (DeepAgents):
   Agent receives message:
   HumanMessage(content="My knee hurts when climbing stairs. I'm 35 years old.")

   Agent's internal reasoning (CoT):
   <think>
   User mentions knee pain while climbing stairs. I should:
   1. Check patient profile for medical history
   2. Search guidelines for "knee pain" and "stair climbing"
   3. Ask follow-up questions about pain characteristics
   </think>

   Agent uses tools:
   ├─ TOOL CALL: read_file("/memories/patient_profile.json")
   │  └─ RESULT: { age: 35, conditions: [], allergies: [] }
   ├─ TOOL CALL: search_guidelines_tool("knee pain stairs")
   │  └─ RESULT: [PDF excerpts about patellofemoral syndrome...]
   └─ FINAL RESPONSE: "Based on your symptoms..."

6. RESPONSE sent back to frontend:
   { response: "Based on your symptoms...", thinking: "..." }

7. AGENT MEMORY PERSISTED:
   MongoDB agent_store collection:
   {
     namespace: ["507f1f77bcf86cd799439011", "filesystem"],
     key: "/memories/patient_profile.json",
     value: { content: [...], updated_at: "2025-01-15T10:30:00Z" }
   }
```

### Agent Decision Tree

```
┌─────────────────────────┐
│ User sends query        │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────────────────────────┐
│ Agent System Prompt:                        │
│ "You are HoloWellness AI Assistant"        │
│ "Check /memories/patient_profile.json"     │
│ "Use search_guidelines_tool for advice"    │
└───────────┬─────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────┐
│ DeepAgents Middleware:                      │
│ - Parses agent's tool calls                 │
│ - Routes filesystem ops to MongoDB          │
│ - Executes search_guidelines_tool           │
└───────────┬─────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────┐
│ Agent generates response                    │
│ - Uses RAG context                          │
│ - References patient data from files        │
│ - Asks follow-up questions                  │
└───────────┬─────────────────────────────────┘
            │
            ▼
┌─────────────────────────┐
│ Response sent to user   │
└─────────────────────────┘
```

---

## 🔧 Backend Components (Deep Dive)

### 1. `agent_factory.py` - The Brain Factory ⭐

**Purpose**: Creates and configures the DeepAgents agent with all necessary components.

**Key Functions**:

```python
def create_holowellness_agent(
    session_id: str,
    user_id: str,
    rag_system: Any,
    model_name: str = "google/gemma-3-27b-it"
) -> Any:
    """
    Creates a Holowellness Chatbot agent using DeepAgents middleware.

    Returns:
        DeepAgents agent with:
        - LLM: Gemma 3 27B via OpenRouter
        - Backend: CompositeBackend (MongoDB + RAM)
        - Tools: File system + RAG search
        - Store: MongoDB virtual filesystem
    """
```

**Architecture Breakdown**:

| Component | Implementation | Purpose |
|-----------|----------------|---------|
| **LLM** | `ChatOpenAI` pointing to OpenRouter | Gemma 3 27B for reasoning & vision |
| **Backend** | `CompositeBackend` | Routes `/memories/` to MongoDB, rest to RAM |
| **Store** | `DeepAgentsMongoStore` | Persistent virtual filesystem |
| **Tools** | `[search_guidelines_tool]` | RAG search through clinical PDFs |
| **System Prompt** | Multi-line string | Instructs agent on behavior |

**Seeding Logic** (Lines 96-139):
```python
# Auto-migrates existing MongoDB data into virtual filesystem
if not mongo_store.get(namespace, "/memories/patient_profile.json"):
    profile = memory_manager.get_patient_profile(user_id)
    mongo_store.put(namespace, path, {"content": [json.dumps(profile)]})
```

**Why This Matters**: New users get instant access to their historical data from MongoDB.

---

### 2. `agent_store.py` - MongoDB Virtual Filesystem ⭐

**Purpose**: Implements LangGraph's `BaseStore` interface to persist agent memory in MongoDB.

**Key Concepts**:

```python
class DeepAgentsMongoStore:
    """
    A virtual filesystem backed by MongoDB.

    Collections:
    - agent_store: Stores all virtual files

    Document Structure:
    {
        "_id": ObjectId("..."),
        "namespace": ["user_id", "filesystem"],
        "key": "/memories/patient_profile.json",
        "value": {
            "content": ["{ \"age\": 35, ... }"],
            "created_at": "2025-01-15T10:00:00Z",
            "modified_at": "2025-01-15T10:30:00Z"
        },
        "updated_at": "2025-01-15T10:30:00Z"
    }
    """
```

**Key Methods**:

| Method | Signature | Purpose |
|--------|-----------|---------|
| `get()` | `get(namespace, key) → Item?` | Retrieve a file |
| `put()` | `put(namespace, key, value)` | Store/update a file |
| `search()` | `search(namespace, filter, limit)` | Query files |

**Namespace Design**:
```
(user_id, "filesystem") → User-specific files
Examples:
- ("507f1f77", "filesystem") + "/memories/patient_profile.json"
- ("507f1f77", "filesystem") + "/memories/recent_workouts.json"
```

**Why MongoDB?**
- ✅ Persistent across server restarts
- ✅ Shared access across multiple agent instances
- ✅ Query capabilities for debugging
- ✅ Backup & recovery built-in

---

### 3. `agent_tools.py` - Custom Agent Tools ⭐

**Purpose**: Define custom tools the agent can use beyond DeepAgents' built-in tools.

**Tools Provided**:

```python
def tool_search_guidelines(query: str, rag_system: Any) -> str:
    """
    Search medical guidelines and exercise protocols.

    Args:
        query: Search query (e.g., "knee pain management")
        rag_system: The RAG system instance

    Returns:
        Formatted string with relevant PDF excerpts
    """
    results = rag_system.search(query, top_k=3)
    return format_results_for_agent(results)
```

**Tool Signature** (for DeepAgents):
```python
@tool
def search_guidelines_tool(query: str):
    """Search medical guidelines and exercise protocols."""
    return tool_search_guidelines(query, rag_system=rag)
```

**Why Custom Tools?**
- DeepAgents provides filesystem tools automatically
- We add domain-specific tools (RAG search)
- Agent decides when to use each tool

---

### 4. `app.py` - Flask API Server

**Key Endpoints**:

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/api/chat` | POST | ✓ | Main chat interface (agent invocation) |
| `/api/auth/signup` | POST | ✗ | User registration |
| `/api/auth/login` | POST | ✗ | User authentication |
| `/api/auth/me` | GET | ✓ | Get current user |
| `/api/memory` | GET | ✓ | Get session history |
| `/api/memory/clear` | POST | ✓ | Clear session history |
| `/api/rag/reindex` | POST | ✓ | Rebuild RAG index |
| `/health` | GET | ✗ | Health check |

**Core Function: `agentic_chat()`**:

```python
def agentic_chat(query: str, user_id: str, session_id: str, image_base64: str = None):
    """
    Invokes the DeepAgents agent for a user query.

    Flow:
    1. Create agent via agent_factory.create_holowellness_agent()
    2. Build messages (with optional multimodal content)
    3. Invoke agent with messages
    4. Extract response and thinking
    5. Save to MongoDB chat history
    6. Return to frontend
    """
    agent = create_holowellness_agent(session_id, user_id, rag)

    messages = []
    if image_base64:
        messages.append(HumanMessage(content=[
            {"type": "text", "text": query},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}}
        ]))
    else:
        messages.append(HumanMessage(content=query))

    result = agent.invoke({"messages": messages})
    return result
```

**Multimodal Support**:
```python
# Frontend sends base64 image:
{ query: "What exercises are shown here?", image_base64: "iVBORw0KGgoAAAANSUhEUg..." }

# Backend creates multimodal message:
HumanMessage(content=[
    {"type": "text", "text": "What exercises are shown here?"},
    {"type": "image_url", "image_url": {"url": "data:image/png;base64,iVBORw..."}}
])

# Gemma 3 27B analyzes image and responds
```

---

### 5. `memory_manager.py` - Data Access Layer

**Purpose**: Provides clean interface to MongoDB collections (legacy compatibility).

**Key Methods**:

| Method | Collection | Purpose |
|--------|------------|---------|
| `get_patient_profile(user_id)` | `patient_profiles` | Fetch medical history |
| `get_active_workouts(user_id)` | `workouts` | Recent exercise logs |
| `get_exercise_library()` | `exercisecategories` | Exercise catalog |
| `get_chat_history(session_id)` | `chatbotinteractions` | Conversation history |
| `add_user_message(...)` | `chatbotinteractions` | Store user message |
| `add_ai_message(...)` | `chatbotinteractions` | Store AI response |

**Why Keep This?**
- ✅ Backward compatibility with v1.0 data
- ✅ Seeding agent's virtual filesystem
- ✅ Direct database operations when needed

---

### 6. `enhanced_rag_qwen.py` - Advanced RAG System

**Purpose**: Two-stage retrieval with reranking for higher quality context.

**Architecture**:

```
Stage 1: Hybrid Retrieval (FAISS + BM25)
├─ FAISS: Semantic similarity (vector embeddings)
├─ BM25: Keyword matching (sparse retrieval)
└─ Merge: Top 20 candidates

Stage 2: Reranking (BGE Reranker)
└─ Cross-encoder scores candidates
└─ Returns top 5 most relevant chunks
```

**Key Features**:
- ✅ FAISS vector index for semantic search
- ✅ BM25 for keyword-based retrieval
- ✅ BGE reranker (cross-encoder) for final ranking
- ✅ GPU/CPU support
- ✅ S3 caching for embeddings

**Why Reranking Matters**:
```
Without reranking (Stage 1 only):
- User: "knee pain while running"
- Retrieves: [doc about knee anatomy, running techniques, pain management, ...]
- Mixed relevance

With reranking (Stage 1 + 2):
- Same query
- Reranker scores: [0.95, 0.87, 0.76, ...]
- Returns ONLY highly relevant docs
- Better LLM context → Better response
```

---

### 7. `auth.py` - Authentication Manager

**Features**:
- ✅ JWT token generation & validation
- ✅ Bcrypt password hashing
- ✅ Optional anonymous chat mode (`ALLOW_ANON_CHAT=true`)
- ✅ Token expiry (configurable)

**Flow**:
```
1. Signup: POST /api/auth/signup
   → Hash password with bcrypt
   → Store in MongoDB users collection
   → Return JWT token

2. Login: POST /api/auth/login
   → Verify password
   → Generate JWT with user_id
   → Return token

3. Protected Routes:
   @require_auth decorator
   → Validates JWT
   → Injects g.user into Flask context
   → Proceeds to route handler
```

---

## 🎨 Frontend Components

### Key Technologies

- **React 18.3.1** - UI framework
- **TypeScript** - Type safety
- **Vite** - Fast dev server & build tool
- **TailwindCSS** - Utility-first styling
- **shadcn/ui** - Radix UI components
- **React Router** - Client-side routing
- **TanStack Query** - Server state management

### Core Components

#### 1. `useChat.ts` - Chat Logic Hook

```typescript
export const useChat = () => {
  const sendMessage = async (text: string, imageBase64?: string) => {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        query: text,
        image_base64: imageBase64,
        session_id: sessionId,
      }),
    });

    const data = await response.json();
    return data;
  };

  return { sendMessage, messages, isLoading };
};
```

#### 2. `ChatContainer.tsx` - Main Chat UI

**Responsibilities**:
- Render conversation history
- Handle scroll-to-bottom
- Display thinking indicator
- Orchestrate child components

#### 3. `ChatInput.tsx` - Input Widget

**Features**:
- ✅ Text input with auto-resize
- ✅ Image upload button
- ✅ Base64 encoding
- ✅ Preview uploaded images
- ✅ Send button with loading state

```typescript
const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
  const file = e.target.files?.[0];
  if (file) {
    const reader = new FileReader();
    reader.onloadend = () => {
      const base64 = reader.result?.toString().split(',')[1];
      setImageBase64(base64);
    };
    reader.readAsDataURL(file);
  }
};
```

#### 4. `ChatMessage.tsx` - Message Renderer

**Features**:
- ✅ User vs AI message styling
- ✅ Markdown rendering (via `marked`)
- ✅ Code syntax highlighting
- ✅ Collapsible "Thinking" section
- ✅ Copy button for code blocks

---

## 📊 Database Schema (MongoDB Atlas)

### Collections Overview

| Collection | Purpose | Key Fields |
|------------|---------|------------|
| `users` | User accounts | `email`, `password_hash`, `created_at` |
| `patient_profiles` | Medical history | `user_id`, `age`, `conditions`, `allergies`, `medications` |
| `workouts` | Exercise logs | `user_id`, `date`, `exercises`, `sets`, `reps`, `weight` |
| `exercisecategories` | Exercise catalog | `category_name`, `exercises[]` |
| `chatbotinteractions` | Chat sessions | `session_id`, `user_id`, `messages[]` |
| `agent_store` | **Virtual filesystem** | `namespace`, `key`, `value` |

### Key Schema: `agent_store` (NEW in v2.0)

```javascript
{
  "_id": ObjectId("..."),
  "namespace": ["507f1f77bcf86cd799439011", "filesystem"],
  "key": "/memories/patient_profile.json",
  "value": {
    "content": [
      "{\n  \"age\": 35,\n  \"conditions\": [\"knee pain\"],\n  \"allergies\": [],\n  \"medications\": []\n}"
    ],
    "created_at": "2025-01-15T10:00:00Z",
    "modified_at": "2025-01-15T10:30:00Z"
  },
  "updated_at": "2025-01-15T10:30:00Z"
}
```

**Indexes**:
```javascript
db.agent_store.createIndex({ namespace: 1, key: 1 }, { unique: true })
```

---

## 🚀 Setup & Installation

### Prerequisites

- **Python 3.9+**
- **Node.js 18+** & npm
- **MongoDB Atlas account** (or local MongoDB)
- **OpenRouter API key** ([openrouter.ai](https://openrouter.ai))
- **AWS Account** (optional, for S3 & Lambda)

### Step 1: Clone Repository

```bash
git clone https://github.com/azamkhan555622848/Holowellness-AI-Agent-.git
cd Holowellness-AI-Agent-/Holowellness_Chatbot_version_1.0
```

### Step 2: Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Mac/Linux)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install DeepAgents
pip install deepagents

# Create .env file
cp .env.example .env
```

**Edit `backend/.env`**:
```env
# MongoDB
MONGO_URI=mongodb+srv://user:password@cluster.mongodb.net/db_holo_wellness?retryWrites=true&w=majority

# OpenRouter API
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxx
OPENROUTER_MODEL=google/gemma-3-27b-it

# Authentication
SECRET_KEY=your-super-secret-jwt-key-change-this
ALLOW_ANON_CHAT=true

# Optional: AWS S3 for RAG PDFs
AWS_REGION=ap-northeast-3
RAG_S3_BUCKET=holowellness
RAG_S3_PREFIX=rag_pdfs/
RAG_SYNC_ON_START=false

# Optional: Enhanced RAG
ENABLE_ENHANCED_RAG=true
```

**Run Backend**:
```bash
python app.py
# Server runs on http://localhost:5000
```

### Step 3: Frontend Setup

```bash
# From project root
npm install

# Start dev server
npm run dev
# Frontend runs on http://localhost:8080
```

### Step 4: Access Application

Open browser to: **http://localhost:8080**

**Test Account** (if anonymous mode disabled):
```
Email: test@holowellness.com
Password: test123
```

---

## ⚙️ Configuration

### Environment Variables Reference

#### Backend (`backend/.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MONGO_URI` | ✓ | - | MongoDB connection string |
| `OPENROUTER_API_KEY` | ✓ | - | OpenRouter API key |
| `OPENROUTER_MODEL` | ✗ | `google/gemma-3-27b-it` | LLM model to use |
| `SECRET_KEY` | ✓ | - | JWT signing secret |
| `ALLOW_ANON_CHAT` | ✗ | `false` | Enable anonymous chat |
| `FLASK_ENV` | ✗ | `development` | `development` or `production` |
| `DEBUG` | ✗ | `False` | Enable debug mode |
| `LOG_LEVEL` | ✗ | `INFO` | Logging level |
| `ENABLE_ENHANCED_RAG` | ✗ | `false` | Use reranking RAG |
| `RAG_S3_BUCKET` | ✗ | - | S3 bucket for PDFs |
| `RAG_S3_PREFIX` | ✗ | `rag_pdfs/` | S3 prefix path |
| `RAG_SYNC_ON_START` | ✗ | `false` | Sync PDFs on startup |

#### Frontend (`.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_USE_PLATFORM_AUTH` | `false` | Use external auth platform |
| `VITE_API_URL` | `/api` | Backend API base URL |

---

## 📚 API Documentation

### Authentication Endpoints

#### `POST /api/auth/signup`

**Request**:
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response**:
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "507f1f77bcf86cd799439011",
    "email": "user@example.com"
  }
}
```

#### `POST /api/auth/login`

**Request**:
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response**: Same as signup

#### `GET /api/auth/me`

**Headers**: `Authorization: Bearer <token>`

**Response**:
```json
{
  "id": "507f1f77bcf86cd799439011",
  "email": "user@example.com",
  "created_at": "2025-01-15T10:00:00Z"
}
```

---

### Chat Endpoints

#### `POST /api/chat`

**Main endpoint for agent interaction.**

**Headers**:
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Request**:
```json
{
  "query": "My knee hurts when running. What exercises should I avoid?",
  "image_base64": "iVBORw0KGgoAAAANSUhEUg...",  // Optional
  "session_id": "abc123",  // Optional (auto-generated if not provided)
  "translate": true  // Optional
}
```

**Response**:
```json
{
  "response": "Based on your knee pain, I recommend avoiding:\n1. High-impact exercises like jumping\n2. Deep squats...",
  "thinking": "User reported knee pain during running. Checked patient profile - no history of injuries. Searched guidelines for 'knee pain running'...",
  "message_id": "msg_abc123",
  "session_id": "abc123"
}
```

---

### Memory Endpoints

#### `GET /api/memory?session_id=abc123`

**Response**:
```json
{
  "session_id": "abc123",
  "history": [
    {
      "role": "user",
      "content": "My knee hurts when running"
    },
    {
      "role": "assistant",
      "content": "I understand you're experiencing knee pain..."
    }
  ]
}
```

#### `POST /api/memory/clear`

**Request**:
```json
{
  "session_id": "abc123"
}
```

**Response**:
```json
{
  "status": "ok",
  "message": "Memory cleared for session abc123"
}
```

---

### RAG Management Endpoints

#### `POST /api/rag/reindex`

**Triggers RAG index rebuild (syncs PDFs from S3 and rebuilds FAISS/BM25 indices).**

**Response**:
```json
{
  "status": "ok",
  "message": "PDFs synced & RAG vectorstore rebuilt.",
  "documents_indexed": 25
}
```

#### `GET /api/rag/status`

**Response**:
```json
{
  "bucket": "holowellness",
  "prefix": "rag_pdfs/",
  "local_pdfs_count": 25,
  "local_pdfs": ["knee_pain_guidelines.pdf", ...],
  "documents_indexed": 25,
  "cache_files": {
    "vector_index.faiss": 1048576,
    "documents.pkl.gz": 524288,
    "bm25_index.pkl": 102400
  }
}
```

---

## 💻 Development Workflow

### Running Locally

```bash
# Terminal 1: Backend
cd backend
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
python app.py

# Terminal 2: Frontend
npm run dev

# Terminal 3: MongoDB (if local)
mongod --dbpath ./data
```

### Code Style

**Python**:
```bash
# Format with black
black backend/

# Lint with flake8
flake8 backend/
```

**TypeScript**:
```bash
# Lint
npm run lint

# Format with Prettier
npm run format
```

### Adding a New Agent Tool

1. **Define tool in `agent_tools.py`**:
```python
def tool_check_vital_signs(patient_id: str) -> str:
    """Check patient's latest vital signs from wearable device."""
    # Implementation
    return json.dumps(vital_signs)
```

2. **Add to tools list in `agent_factory.py`**:
```python
tools = [
    search_guidelines_tool,
    check_vital_signs_tool  # NEW
]
```

3. **Update system prompt**:
```python
system_prompt = f"""
...
- **Vital Signs**: Check `/memories/vital_signs.json` or use `check_vital_signs_tool`.
...
"""
```

4. **Test**:
```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"query": "Check my heart rate"}'
```

---

## 🧪 Testing

### Unit Tests

```bash
# Backend
cd backend
pytest tests/

# Frontend
npm test
```

### Test Files

```bash
backend/test_rag.py              # Test RAG retrieval
backend/test_enhanced_rag.py     # Test reranking
backend/test_multimodal.py       # Test image analysis
backend/test_fitness_rag.py      # Test exercise search
```

### Manual Testing

```bash
# Test agent with RAG
python backend/test.py

# Test enhanced RAG
python backend/test_enhanced.py
```

---

## 🌍 Deployment

### Production Checklist

- [ ] Set `FLASK_ENV=production`
- [ ] Set `DEBUG=False`
- [ ] Use strong `SECRET_KEY`
- [ ] Enable HTTPS
- [ ] Configure CORS origins
- [ ] Set up MongoDB Atlas with IP whitelist
- [ ] Use Gunicorn with multiple workers
- [ ] Set up reverse proxy (Nginx)
- [ ] Configure S3 for RAG PDFs
- [ ] Enable monitoring (CloudWatch, Sentry)
- [ ] Set up CI/CD pipeline

### Deployment Methods

#### 1. AWS EC2 (Recommended)

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for full instructions.

Quick steps:
```bash
# SSH into EC2
ssh -i key.pem ubuntu@ec2-xx-xx-xx-xx.compute.amazonaws.com

# Clone repo
git clone https://github.com/azamkhan555622848/Holowellness-AI-Agent-.git
cd Holowellness-AI-Agent-/Holowellness_Chatbot_version_1.0

# Run deployment script
./deploy/deploy-app.sh
```

#### 2. Docker (Alternative)

```bash
# Build
docker build -t holowellness-agent .

# Run
docker run -p 5000:5000 \
  -e MONGO_URI=$MONGO_URI \
  -e OPENROUTER_API_KEY=$OPENROUTER_API_KEY \
  holowellness-agent
```

---

## 🔄 Migration Guide (from v1.0 to v2.0)

### Data Migration

**v2.0 automatically migrates v1.0 data!**

When you first create an agent for a user, `agent_factory.py` will:
1. Check if `/memories/patient_profile.json` exists in agent_store
2. If not, fetch data from legacy collections:
   - `patient_profiles`
   - `workouts`
   - `exercisecategories`
3. Seed the virtual filesystem with this data

**No manual migration needed!**

### Code Migration

#### Before (v1.0):
```python
# app.py
@app.route('/api/chat', methods=['POST'])
def chat():
    query = request.json['query']
    user_id = request.json['user_id']

    # Direct MongoDB query
    profile = memory_manager.get_patient_profile(user_id)

    # Direct RAG call
    response = rag.generate_answer(query, profile)

    return jsonify({'response': response})
```

#### After (v2.0):
```python
# app.py
@app.route('/api/chat', methods=['POST'])
@require_auth
def chat():
    query = request.json['query']
    user_id = g.user['id']

    # Agent handles everything
    response = agentic_chat(query, user_id, session_id)

    return jsonify(response)

# Agent autonomously:
# 1. Reads profile from /memories/patient_profile.json
# 2. Searches RAG if needed
# 3. Decides what to ask
```

### API Changes

| v1.0 Endpoint | v2.0 Endpoint | Change |
|---------------|---------------|--------|
| `POST /api/chat` | `POST /api/chat` | Now requires JWT auth |
| N/A | `POST /api/auth/signup` | New |
| N/A | `POST /api/auth/login` | New |
| `GET /api/profile` | Agent reads from VFS | Removed |

---

## 🐛 Troubleshooting

### Common Issues

#### 1. "Agent not responding"

**Symptoms**: Request hangs or times out

**Solutions**:
```bash
# Check if OpenRouter API key is valid
curl https://openrouter.ai/api/v1/models \
  -H "Authorization: Bearer $OPENROUTER_API_KEY"

# Check backend logs
tail -f backend/logs/app.log

# Verify MongoDB connection
mongo $MONGO_URI --eval "db.adminCommand('ping')"
```

#### 2. "Virtual filesystem empty"

**Symptoms**: Agent says "No patient data found"

**Solutions**:
```python
# Check agent_store collection
use db_holo_wellness
db.agent_store.find({"namespace": ["{user_id}", "filesystem"]})

# Manually seed data
python backend/seed_agent_memory.py --user-id 507f1f77bcf86cd799439011
```

#### 3. "RAG returns irrelevant results"

**Solutions**:
```bash
# Rebuild RAG index
curl -X POST http://localhost:5000/api/rag/reindex \
  -H "Authorization: Bearer $TOKEN"

# Check PDF count
curl http://localhost:5000/api/rag/status

# Test RAG directly
python backend/test_rag.py --query "knee pain"
```

#### 4. "Frontend can't connect to backend"

**Solutions**:
```bash
# Check CORS settings in backend/.env
CORS_ORIGINS=http://localhost:8080,http://localhost:5173

# Verify backend is running
curl http://localhost:5000/health

# Check browser console for errors
```

---

## 🤝 Contributing

### Development Setup

1. Fork the repository
2. Create feature branch: `git checkout -b feature/my-feature`
3. Make changes
4. Run tests: `pytest backend/tests && npm test`
5. Commit: `git commit -m "Add my feature"`
6. Push: `git push origin feature/my-feature`
7. Open Pull Request

### Code Standards

- **Python**: Follow PEP 8, use type hints
- **TypeScript**: Strict mode enabled
- **Commits**: Conventional Commits format
- **PRs**: Include tests and documentation updates

---

## 📄 License

**Proprietary** - HoloWellness

© 2025 HoloWellness. All rights reserved.

---

## 📞 Support

- **Email**: support@holowellness.com
- **Docs**: [docs.holowellness.com](https://docs.holowellness.com)
- **Issues**: [GitHub Issues](https://github.com/azamkhan555622848/Holowellness-AI-Agent-/issues)

---

## 🙏 Acknowledgments

- **DeepAgents**: Middleware framework
- **LangChain**: Agent orchestration
- **OpenRouter**: LLM API gateway
- **Google**: Gemma 3 27B model
- **shadcn/ui**: UI components

---

**Built with ❤️ by the HoloWellness Team**
