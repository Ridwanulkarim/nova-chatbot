# Pluto AI — Autonomous Multi-Provider Agentic AI Platform

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white)](https://pluto-chatbot-kappa.vercel.app/)
[![Backend](https://img.shields.io/badge/FastAPI-0.109+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Frontend](https://img.shields.io/badge/React%2018-Vite%205-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://reactjs.org)
[![Database](https://img.shields.io/badge/Database-Neon%20PostgreSQL-00E599?style=for-the-badge&logo=postgresql&logoColor=black)](https://neon.tech)
[![Python](https://img.shields.io/badge/Python-3.9%20%7C%203.10%20%7C%203.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

> 🚀 **Live Production Application**: [https://pluto-chatbot-kappa.vercel.app/](https://pluto-chatbot-kappa.vercel.app/)  
> 🔗 **GitHub Repository**: [https://github.com/Ridwanulkarim/pluto-chatbot](https://github.com/Ridwanulkarim/pluto-chatbot)

---

## 📖 Table of Contents
- [Executive Overview](#-executive-overview)
- [System Architecture](#-system-architecture)
- [Custom Agentic Orchestrator Engine](#-custom-agentic-orchestrator-engine)
- [Database & High-Availability Persistence](#-database--high-availability-persistence)
- [Key Features & Agentic Capabilities](#-key-features--agentic-capabilities)
- [Technology Stack](#-technology-stack)
- [API Reference](#-api-reference)
- [Repository Structure](#-repository-structure)
- [Getting Started & Local Setup](#-getting-started--local-setup)
- [Automated Testing Suite](#-automated-testing-suite)
- [Production Deployment](#-production-deployment)
- [License](#-license)

---

## 🌟 Executive Overview

**Pluto AI** is a production-grade, full-stack, autonomous multimodal AI conversational platform. Engineered for real-time responsiveness and zero-downtime persistence, Pluto AI combines a modern **React 18** interface with a high-throughput **FastAPI** backend, resilient **Neon Cloud PostgreSQL**, and a proprietary **Custom Agentic Orchestrator**.

Unlike conventional chatbots that simply wrap a single LLM API call, Pluto AI implements an **autonomous decision-making agent pipeline** capable of:
1. **Dynamic Intent Classification & Routing**: Autonomously identifying queries requiring external computation, search, visual inspection, or image synthesis.
2. **Tool & Code Execution**: Invoking symbolic mathematics engines (SymPy), real-time web crawlers (DuckDuckGo), and fast text-to-image synthesis pipelines.
3. **Multi-Turn Context & Document Continuity**: Maintaining conversational state, user memory, and document retrieval (RAG) across conversational turns.
4. **Resilient Serverless Persistence**: Architected with multi-database failover guaranteeing zero data loss across mobile and desktop devices.

---

## 🏛️ System Architecture

Pluto AI employs a decoupled, micro-modular architecture optimized for serverless edge deployment on **Vercel** with persistent connections to **Neon PostgreSQL**.

```mermaid
flowchart TB
    subgraph ClientLayer ["Frontend Client Layer (Vite + React 18)"]
        UI["Modern Responsive UI (Tailwind CSS)"]
        Voice["Hands-Free Voice & Audio Synthesis"]
        SSEClient["SSE Stream Parser (AbortController)"]
        State["Auth & Chat State Context"]
    end

    subgraph GatewayLayer ["API Gateway & Security (FastAPI)"]
        CORS["CORS & Origin Filtering"]
        Auth["OWASP PBKDF2 Hashing & JWT Bearer"]
        Quota["Daily Quota Enforcer (50 msg / 10 img)"]
        Router["Versioned REST & SSE Streaming Routes (/api/v1)"]
    end

    subgraph AgentLayer ["Custom Agentic Orchestration Layer"]
        Orchestrator["ToolOrchestrator (Intent Analyzer)"]
        Math["SymPy Symbolic Math Engine"]
        Search["Live Web Grounding (DuckDuckGo)"]
        RAG["Document RAG & Chunk Retriever"]
        Vision["Multimodal Vision Continuity Engine"]
        ImgGen["Fast Turbo Image Studio"]
        Factory["Dynamic AI Provider Factory"]
    end

    subgraph ProviderLayer ["Upstream Model Providers"]
        Gemini["Google Gemini 3.5 Flash (Vision & Reasoning)"]
        Groq["Groq LPU (Llama 3.3 70B & OSS-120B)"]
        OpenAI["OpenAI GPT-4o / GPT-OSS"]
    end

    subgraph PersistenceLayer ["Database & Storage Infrastructure"]
        NeonDB[("Primary: Neon Serverless PostgreSQL\n(SSL Pooling / 9 Relational Tables)")]
        SQLiteFailover[("Failover: Resilient In-Memory/SQLite\n(Zero-Downtime High Availability)")]
        FS["Uploads / Cloud Storage (Documents & Images)"]
    end

    %% Client to Gateway
    UI --> State
    Voice --> Router
    SSEClient <--> Router
    State --> Router
    Router --> CORS --> Auth --> Quota

    %% Gateway to Agent
    Quota --> Orchestrator

    %% Agent Routing
    Orchestrator --> Math
    Orchestrator --> Search
    Orchestrator --> RAG
    Orchestrator --> Vision
    Orchestrator --> ImgGen
    Orchestrator --> Factory

    %% Providers
    Factory --> Gemini
    Factory --> Groq
    Factory --> OpenAI

    %% Persistence
    Router <--> NeonDB
    NeonDB -.->|On Network/Auth Failure| SQLiteFailover
    RAG <--> FS
    Router <--> FS
```

---

## 🧠 Custom Agentic Orchestrator Engine

### Why a Custom Orchestrator Instead of Heavy Frameworks?
While frameworks like LangGraph, AutoGen, or CrewAI provide multi-agent primitives, they introduce substantial memory footprints, complex state serialization, and severe **Cold-Start Latency (2–4 seconds)** on serverless platforms like Vercel and AWS Lambda.

Pluto AI features an in-house **Lightweight Custom Agentic Orchestrator** ([`backend/app/ai/orchestrator.py`](backend/app/ai/orchestrator.py)) engineered for sub-millisecond dispatching, deterministic execution, and seamless stream pipelining.

```mermaid
sequenceDiagram
    autonumber
    actor User as User / Client
    participant API as FastAPI Router (/messages)
    participant Orch as ToolOrchestrator
    participant Tool as Specialized Engine (Math/Web/RAG/Image)
    participant Provider as AI Provider Factory (Gemini/Groq/OpenAI)
    participant DB as Neon PostgreSQL

    User->>API: POST /api/v1/conversations/{id}/messages (prompt, attachments)
    API->>DB: Persist User Message & Check Quota
    API->>Orch: analyze_intent(query, attachments)

    alt Image Generation Intent (e.g. "draw a neon skyline")
        Orch-->>API: Route: IMAGE_GENERATION
        API->>Tool: image_service.generate_image(prompt)
        Tool-->>API: Rendered Image URL (Turbo Mode)
        API->>DB: Save Assistant Image Card
        API-->>User: Stream Image Card & Markdown
    else Mathematical / Analytical Intent (e.g. "integrate x^2 * sin(x)")
        Orch-->>API: Route: MATH_SOLVER
        API->>Tool: math_service.solve_expression(query)
        Tool-->>API: Exact SymPy Analytical Solution & Steps
        API->>Provider: Stream reasoning grounded with verified math steps
        Provider-->>User: SSE Token Stream ($LaTeX$ output)
    else Real-Time / Temporal Intent (e.g. "latest tech news today")
        Orch-->>API: Route: WEB_SEARCH
        API->>Tool: search_service.search(query)
        Tool-->>API: Live Web Sources & Grounding Snippets
        API->>Provider: Synthesize response with clickable source citations
        Provider-->>User: SSE Token Stream + Citations
    else Document Context Attached (e.g. "explain page 3 of this pdf")
        Orch-->>API: Route: DOCUMENT_RAG
        API->>Tool: rag_service.search_relevant_chunks(file_ids, query)
        Tool-->>API: Vector Chunks & Semantic Text Excerpts
        API->>Provider: Ground answer strictly on document text
        Provider-->>User: SSE Token Stream
    else Multimodal Image / Screenshot Attached
        Orch-->>API: Route: VISION_MULTIMODAL
        API->>Tool: vision_service.validate_and_optimize(image)
        API->>Provider: Dispatch to Vision-capable LLM (Gemini 3.5 / GPT-4o)
        Provider-->>User: SSE Token Stream with pixel-level answers
    end

    API->>DB: Persist Assistant Response & Update Conversation
```

### Core Autonomous Services:
| Module | File | Role & Technology |
|---|---|---|
| **Intent Orchestrator** | `app/ai/orchestrator.py` | Heuristic and semantic intent parser routing requests to specialized tools. |
| **Math Solver** | `app/ai/math_service.py` | Python **SymPy** symbolic algebra engine for analytical calculus, equations, and linear algebra. |
| **Web Grounding** | `app/ai/search_service.py` | Live DuckDuckGo search integration with automated source extraction and citation formatting. |
| **Document RAG** | `app/ai/rag_service.py` | Text extraction (PyPDF/DOCX), recursive chunking, overlap preservation, and cosine relevance ranking. |
| **Image Generation** | `app/ai/image_service.py` | Text-to-image synthesis pipeline with watermark-free turbo acceleration. |
| **Vision Continuity** | `app/ai/vision_service.py` | Base64 optimization, dimension verification, and multi-turn visual memory carry-forward. |

---

## 🗄️ Database & High-Availability Persistence

Pluto AI connects to a high-performance **Neon Serverless PostgreSQL** database with an automated schema provisioner and zero-downtime resilient fallback:

```mermaid
classDiagram
    direction LR
    class User {
        +String id (PK)
        +String email (Unique)
        +String hashed_password
        +Boolean is_active
        +DateTime created_at
    }

    class Conversation {
        +String id (PK)
        +String user_id (FK)
        +String title
        +String model
        +String system_prompt
        +Boolean is_pinned
        +DateTime updated_at
    }

    class Message {
        +String id (PK)
        +String conversation_id (FK)
        +String role (user/assistant)
        +Text content
        +JSON attachments
        +String model
        +DateTime created_at
    }

    class Document {
        +String id (PK)
        +String user_id (FK)
        +String filename
        +String file_path
        +Integer file_size
        +String mime_type
        +DateTime created_at
    }

    class DocumentChunk {
        +String id (PK)
        +String document_id (FK)
        +Integer chunk_index
        +Text content
    }

    class UserMemory {
        +String id (PK)
        +String user_id (FK)
        +Text content
        +DateTime created_at
    }

    class UserSettings {
        +String id (PK)
        +String user_id (FK)
        +Float temperature
        +Text system_instructions
        +Boolean web_search_enabled
        +Boolean memory_enabled
    }

    class UserDailyUsage {
        +String id (PK)
        +String user_id (FK)
        +Date date
        +Integer message_count
        +Integer image_count
    }

    User "1" --> "*" Conversation : owns
    User "1" --> "*" Document : uploads
    User "1" --> "*" UserMemory : remembers
    User "1" --> "1" UserSettings : configures
    User "1" --> "*" UserDailyUsage : tracks
    Conversation "1" --> "*" Message : contains
    Document "1" --> "*" DocumentChunk : split into
```

### High-Availability Resilient Session (`_ResilientSessionMaker`)
1. **Cloud Primary**: All production traffic executes directly against **Neon PostgreSQL** via `pg8000` / `psycopg2` connection pooling.
2. **Auto-Provisioning**: On startup, `_init_primary_schema()` provisions all 9 relational tables automatically.
3. **Transparent Fallback**: If an upstream network partition or authentication failure occurs, the engine dynamically activates a local SQLite fallback (`/tmp/pluto_ai.db`), guaranteeing **zero downtime** for active user sessions.
4. **Diagnostic Telemetry**: Real-time connection status, table health, and failover diagnostics are exposed at `/api/db-status`.

---

## ⚡ Key Features & Agentic Capabilities

- **⚡ Real-Time SSE Token Streaming**: Token-by-token streaming with low time-to-first-token (TTFT) and client-side abort support (`AbortController`).
- **🎙️ Hands-Free Live Voice Assistant**:
  - Full-screen interactive voice mode featuring a pulsating multi-layer glowing audio visualizer.
  - Native Web Speech API recognition and speech synthesis loop.
  - Microphone dictation in chat composer + Read Aloud for assistant answers.
- **🎨 AI Image Studio & Photorealistic Synthesis**:
  - Direct natural language prompts (e.g. *"draw a futuristic robot in cyberpunk style"*) rendered as high-res cards with one-click direct download.
- **📎 Native Multimodal Vision**:
  - Full pixel understanding for math worksheets, exam papers, diagrams, flowcharts, and code screenshots.
  - Multi-turn vision memory: ask questions about an image uploaded turns ago without re-uploading.
- **📚 Document Intelligence & RAG**:
  - Native extraction and vector chunking for PDF, DOCX, TXT, and Markdown files.
  - Multi-turn document context retention.
- **🌐 Real-Time Web Grounding**:
  - Integrated search retrieving live 2026 data, breaking news, and market statistics with clickable domain citations.
- **🛡️ Enterprise-Grade Authentication & Isolation**:
  - OWASP PBKDF2-HMAC-SHA256 password hashing (200,000 iterations).
  - Cryptographically signed JWT tokens with strict user isolation across all endpoints.
- **📊 Fair-Use Quota Management**:
  - Daily limit tracking (50 messages / 10 image generations) with automatic UTC midnight resets.

---

## 🏗️ Technology Stack

| Domain | Technology | Description |
|---|---|---|
| **Frontend Framework** | **React 18 + Vite 5** | High-performance SPA with fast hot module replacement (HMR). |
| **Styling & Icons** | **Tailwind CSS 3.4 + Lucide React** | Responsive dark navy theme with custom scrollbars and animations. |
| **Backend Framework** | **FastAPI + Uvicorn** | Asynchronous ASGI Python framework with Pydantic v2 validation. |
| **Primary Database** | **Neon PostgreSQL** | Serverless cloud PostgreSQL with auto-scaling and connection pooling. |
| **ORM & Migrations** | **SQLAlchemy 2.0** | Object-Relational Mapping with connection resilience. |
| **AI Providers** | **Google Gemini, Groq, OpenAI** | Multimodal LLMs (Gemini 3.5 Flash, Llama 3.3 70B, GPT-4o, GPT-OSS). |
| **Symbolic Math** | **SymPy** | Pure Python computer algebra system for exact calculus and equations. |
| **Web Grounding** | **DuckDuckGo Search API** | Live search integration without requiring commercial search API keys. |
| **Testing** | **unittest & FastAPI TestClient** | Comprehensive unit, integration, quota, and security test suites. |

---

## 🔌 API Reference

### Core Endpoints

| Method | Endpoint | Description | Auth Required |
|---|---|---|:---:|
| `POST` | `/api/v1/auth/register` | Register a new user account | ❌ |
| `POST` | `/api/v1/auth/login` | Authenticate and obtain JWT bearer token | ❌ |
| `GET` | `/api/v1/auth/me` | Fetch authenticated user profile & quota | ✅ |
| `GET` | `/api/v1/conversations` | List user's conversations (supports search & pin) | ✅ |
| `POST` | `/api/v1/conversations` | Create a new conversation | ✅ |
| `DELETE` | `/api/v1/conversations/{id}` | Delete conversation and associated messages | ✅ |
| `GET` | `/api/v1/conversations/{id}/messages` | Retrieve conversation message history | ✅ |
| `POST` | `/api/v1/conversations/{id}/messages` | Send message and receive **Server-Sent Events (SSE)** stream | ✅ |
| `POST` | `/api/v1/files/upload` | Upload document or image attachment | ✅ |
| `POST` | `/api/v1/image/generate` | Generate AI image from prompt | ✅ |
| `GET` | `/api/db-status` | Database connection telemetry & active tables | ❌ |
| `GET` | `/api/v1/health` | Service health status | ❌ |

---

## 📂 Repository Structure

```
pluto-chatbot/
├── backend/
│   ├── app/
│   │   ├── ai/                      # Agentic modules & AI provider abstractions
│   │   │   ├── orchestrator.py      # Core ToolOrchestrator (Intent Analyzer & Router)
│   │   │   ├── provider_factory.py  # Multi-provider LLM factory (Gemini, Groq, OpenAI)
│   │   │   ├── math_service.py      # SymPy symbolic math execution engine
│   │   │   ├── search_service.py    # DuckDuckGo live web grounding & citations
│   │   │   ├── rag_service.py       # Document RAG (chunking & semantic retrieval)
│   │   │   ├── vision_service.py    # Native vision validation & image processing
│   │   │   └── image_service.py     # High-speed Turbo image generation studio
│   │   ├── api/                     # REST & Streaming route controllers
│   │   │   ├── v1/
│   │   │   │   ├── endpoints/       # auth, conversations, messages, files, image, settings
│   │   │   │   └── api_router.py
│   │   │   └── deps.py              # JWT authentication & user dependency injection
│   │   ├── core/                    # Config, security hashing, and quota engine
│   │   │   ├── config.py            # Environment settings & URL normalizer
│   │   │   ├── security.py          # PBKDF2 hashing & JWT encoding
│   │   │   └── quota.py             # Message & image daily quota management
│   │   ├── database/                # Database engine, connection pooling, and resilient sessions
│   │   │   ├── session.py           # Resilient session maker with zero-downtime fallback
│   │   │   └── connection.py        # PostgreSQL / SQLite configuration
│   │   ├── models/                  # SQLAlchemy ORM models (9 relational tables)
│   │   ├── schemas/                 # Pydantic v2 request/response validation schemas
│   │   └── main.py                  # FastAPI application entrypoint & middleware
│   ├── tests/                       # Automated test suite (Auth, Quota, Isolation, RAG)
│   └── requirements.txt             # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── chat/                # ChatArea, ChatComposer, MessageItem, MarkdownContent
│   │   │   ├── voice/               # Full-screen Hands-Free Live Voice Assistant
│   │   │   ├── sidebar/             # Conversation history, pinned chats, and search
│   │   │   └── modals/              # Settings, Documents, and Authentication modals
│   │   ├── contexts/                # AuthContext and ChatContext providers
│   │   ├── services/                # Axios API client and SSE streaming parser
│   │   ├── App.jsx                  # Main application shell
│   │   └── main.jsx
│   ├── tailwind.config.js
│   └── vite.config.js
├── vercel.json                      # Vercel serverless deployment routing
└── README.md
```

---

## 🚀 Getting Started & Local Setup

### 1. Prerequisites
- **Python 3.9+**
- **Node.js 18+** and **npm**
- Modern Web Browser (Chrome, Brave, Edge, or Safari)

### 2. Clone the Repository
```bash
git clone https://github.com/Ridwanulkarim/pluto-chatbot.git
cd pluto-chatbot
```

### 3. Backend Setup
```bash
cd backend

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env configuration
cp ../.env.example .env
```

Configure your `.env` file:
```env
# Database (Defaults to SQLite for local development; Neon PostgreSQL for production)
DATABASE_URL=postgresql://user:password@ep-host.aws.neon.tech/neondb?sslmode=require

# AI Provider Keys
GEMINI_API_KEY=your_gemini_api_key_here
GROQ_API_KEY=your_groq_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# Security
SECRET_KEY=generate_a_random_32_byte_hex_string
ENVIRONMENT=development
```

Start the backend server:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
*Interactive Swagger API documentation: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)*

### 4. Frontend Setup
In a new terminal window:
```bash
cd frontend

# Install npm dependencies
npm install

# Start Vite development server
npm run dev
```
*Open [http://localhost:5173](http://localhost:5173) in your browser.*

---

## 🧪 Automated Testing Suite

Pluto AI includes a comprehensive automated test suite verifying security, multi-user isolation, mathematical solving, quota deduction, and RAG indexing.

To execute all test suites:
```bash
cd backend
PYTHONPATH=. .venv/bin/python3 -m unittest discover -s tests -p "test_*.py" -v
```

### Verification Matrix:
- ✔️ **User Authentication**: PBKDF2 hashing, duplicate rejection, tamper-evident JWT tokens.
- ✔️ **Multi-Tenant Isolation**: Confirms User A cannot read or modify User B's conversations or files.
- ✔️ **Daily Quota Enforcement**: Verifies 50 messages/day and 10 images/day limit with auto-refund on failed calls.
- ✔️ **RAG Chunking**: Validates recursive document splitters and citation accuracy.
- ✔️ **SymPy Execution**: Confirms analytical symbolic mathematics calculations.

---

## 🌐 Production Deployment

### Vercel Serverless (Recommended)
This repository includes a pre-configured [`vercel.json`](vercel.json) orchestrating both the frontend SPA and the Python serverless backend functions:
1. Fork or push this repository to GitHub.
2. Import the project into your [Vercel Dashboard](https://vercel.com).
3. In **Settings -> Environment Variables**, configure:
   - `DATABASE_URL`: Your verified **Neon PostgreSQL** pooled connection string.
   - `GEMINI_API_KEY`: Google Gemini API key.
   - `GROQ_API_KEY`: Groq Cloud API key.
   - `SECRET_KEY`: Secure random HMAC secret.
4. Deploy! The live application will be available at your `*.vercel.app` domain.

---

## 📄 License
This project is open-source and distributed under the **[MIT License](LICENSE)**.

---

<p align="center">
  <b>Built with ❤️ by Ridwanul Karim</b><br>
  <i>Empowering next-generation conversational AI with autonomous agentic intelligence.</i>
</p>
