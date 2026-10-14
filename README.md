# Pluto AI - Production-Grade Full-Stack AI Chatbot

[![Live Demo](https://img.shields.io/badge/Live_Demo-Vercel-success?style=for-the-badge&logo=vercel)](https://pluto-chatbot-3gfbb3cqn-ridwanulkarims-projects.vercel.app/)
[![GitHub Repo](https://img.shields.io/badge/GitHub-Repository-blue?style=for-the-badge&logo=github)](https://github.com/Ridwanulkarim/pluto-chatbot)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

> 🚀 **Live Production URL**: [https://pluto-chatbot-3gfbb3cqn-ridwanulkarims-projects.vercel.app/](https://pluto-chatbot-3gfbb3cqn-ridwanulkarims-projects.vercel.app/)  
> *(Production Domain: [https://pluto-chatbot.vercel.app/](https://pluto-chatbot.vercel.app/))*

Pluto AI is a full-stack, autonomous AI conversational platform engineered with FastAPI, React 18, Tailwind CSS, and SQLAlchemy. Inspired by the best of ChatGPT, Claude, and Gemini, Pluto AI delivers a responsive dark-themed workspace, real-time Server-Sent Events (SSE) token streaming, multi-provider LLM abstraction (OpenAI, Groq, Gemini, Ollama), Retrieval-Augmented Generation (RAG) for document Q&A, real-time web search with source citations, and user-isolated persistent storage.

---

## 🌟 Key Features

- **⚡ Real-Time SSE Token Streaming**: Ultra-responsive chat experience streaming token-by-token completions with user cancellation (`AbortController` support).
- **🎙️ AI Voice Assistant & Hands-Free Voice Mode**:
  - **Live Voice Mode (ChatGPT style)**: Full-screen interactive voice session featuring a pulsating multi-layer glowing audio orb, real-time speech detection, automatic AI reply synthesis, and hands-free turn-taking loop.
  - **Voice Dictation**: Microphone button in chat composer for instant speech-to-text.
  - **Read Aloud**: Speaker button on assistant responses to speak answers with natural voice synthesis.
- **🎨 AI Image & Photo Generation**:
  - Generate photorealistic and artistic images directly in conversation using natural language (e.g. `generate an image of a cybernetic panther`) or the Image button.
  - Instant image card rendering with one-click direct download button.
- **📎 Multimodal File & Media Support**:
  - Attach photos (`.png`, `.jpg`, `.webp`, `.gif`), documents (`.pdf`, `.txt`, `.docx`), and videos (`.mp4`, `.webm`).
  - Visual thumbnail previews in message bubbles with media badges.
- **⚡ Daily Usage Quota System**:
  - Fair-use tracking of daily free messages (50/day) and AI image generations (10/day).
  - Resets automatically at midnight UTC.
  - Real-time Quota Indicator Pill and progress popover in the top header.
- **🧠 Multi-Provider AI Abstraction**: Clean adapter architecture supporting OpenAI and Groq (`openai/gpt-oss-120b`, `qwen/qwen3.8-27b`, `openai/gpt-oss-20b`).
- **📚 Document Intelligence & RAG**: Upload documents to ground AI answers with citation references.
- **🌐 Web-Grounded Search**: Search the live web with DuckDuckGo integration and cite sources with clickable URLs.
- **🛡️ Enterprise Security & Data Isolation**:
  - OWASP PBKDF2-HMAC-SHA256 password hashing with 200,000 rounds and random salt.
  - Cryptographically signed HMAC-SHA256 bearer tokens.
  - Strict resource ownership checks on every conversation, document, and memory.
- **💾 Conversation Management**: Pinned chats, date grouping, inline renaming, search filtering, message editing, regeneration, and feedback thumbs up/down.
- **🔗 Shareable Links**: Generate public, revocable read-only links for any conversation.
- **🎨 Modern Dark Navy Interface**: Built with Tailwind CSS, custom scrollbars, syntax-highlighted code blocks with one-click copy buttons, and responsive mobile navigation.

---

## 🏗️ Technology Stack

| Layer | Technologies |
|---|---|
| **Frontend** | React 18, Vite 5, Tailwind CSS 3.4, Lucide React icons |
| **Backend** | Python 3.9+, FastAPI, Pydantic v2, SQLAlchemy 2.0, Uvicorn |
| **Database** | SQLite (zero-config local development) / PostgreSQL (production) |
| **AI Providers** | OpenAI SDK, Groq (OpenAI-compatible), DuckDuckGo Search |
| **Testing** | Python `unittest` & FastAPI `TestClient` (Automated API + E2E suite) |

---

## 📂 Project Structure

```
nova-ai/
├── backend/
│   ├── app/
│   │   ├── ai/               # AI Provider abstraction, RAG, Web Search
│   │   │   ├── base_provider.py
│   │   │   ├── openai_provider.py
│   │   │   ├── groq_provider.py
│   │   │   ├── provider_factory.py
│   │   │   ├── rag_service.py
│   │   │   └── search_service.py
│   │   ├── api/              # REST & SSE Route controllers
│   │   │   ├── v1/
│   │   │   │   ├── endpoints/ # auth, conversations, messages, files, settings, health
│   │   │   │   └── api_router.py
│   │   │   └── deps.py       # Auth dependencies & bearer token verification
│   │   ├── core/             # Configuration & security helpers
│   │   │   ├── config.py
│   │   │   └── security.py
│   │   ├── database/         # SQLAlchemy engine & session factory
│   │   ├── models/           # ORM models (users, conversations, messages, documents)
│   │   ├── schemas/          # Pydantic v2 request/response contracts
│   │   └── main.py           # FastAPI entry point & CORS
│   ├── tests/                # Automated unit, integration, and E2E test suites
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── chat/         # ChatArea, ChatComposer, MessageItem, MarkdownContent, WelcomeScreen
│   │   │   ├── sidebar/      # Sidebar with date grouping & search
│   │   │   └── modals/       # AuthModal, SettingsModal, DocumentModal, ShareModal
│   │   ├── contexts/         # AuthContext, ChatContext
│   │   ├── services/         # api.js, chatStream.js (SSE parser)
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.js
├── scripts/
│   ├── start.sh              # Unified launcher
│   ├── start_backend.sh
│   └── start_frontend.sh
├── .env.example
├── .gitignore
└── README.md
```

---

## 🚀 Quickstart & Local Setup on macOS

### 1. Prerequisites
- macOS (Intel or Apple Silicon)
- Python 3.9+ installed
- Node.js 18+ and npm installed

### 2. Configure Environment
Copy `.env.example` to `.env` (or `nova_ai.env`):
```bash
cp .env.example nova_ai.env
```
Provide your desired AI Provider API Key:
```env
# Add either an OpenAI key or Groq key (or both)
OPENAI_API_KEY=your_openai_api_key_here
GROQ_API_KEY=your_groq_api_key_here

# Default model
DEFAULT_MODEL=gpt-4o-mini
```

### 3. Start Backend & Frontend
You can launch both services together using the provided script:
```bash
./scripts/start.sh
```

Or start them individually:

**Backend (Port 8000):**
```bash
./scripts/start_backend.sh
```
*API documentation is interactively available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).*

**Frontend (Port 5180):**
```bash
./scripts/start_frontend.sh
```
*Access the web UI at [http://localhost:5180](http://localhost:5180).*

---

## 🧪 Running Automated Tests

Run the backend unit, security, API integration, and full E2E test suite:
```bash
PYTHONPATH=./backend/.venv/lib/python3.9/site-packages:./backend python3 -m unittest discover -s backend/tests -p "test_*.py" -v
```

All 9 test suites verify:
- User registration, duplicate detection, and login
- Tamper-evident JWT token creation and expiration
- Salted PBKDF2 password verification
- Multi-user data isolation (User A cannot access User B's conversations)
- RAG text chunking and web search citation formatting
- Document upload and chunk indexing
- Real-time SSE streaming and message persistence

---

## 🛡️ Production Deployment Guide

### Frontend (e.g. Vercel / Netlify / Cloudflare Pages)
1. Build the production assets:
   ```bash
   cd frontend && npm run build
   ```
2. Set the environment variable:
   `VITE_API_URL=https://api.yourdomain.com`

### Backend (e.g. Docker / Railway / Render / AWS)
1. Configure `DATABASE_URL` pointing to managed PostgreSQL:
   ```env
   DATABASE_URL=postgresql+psycopg2://user:password@pg-host:5432/nova_ai
   ENVIRONMENT=production
   DEBUG=False
   SECRET_KEY=generate_with_python_secrets_token_hex_32
   ```
2. Run with standard production command:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
   ```

---

## 📄 License
MIT License. Built with ❤️ for next-generation AI workflows.
