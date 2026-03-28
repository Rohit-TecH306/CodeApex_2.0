# AI Bank Assistance - Domain-Safe Offline & Online Banking Assistant

## 🚀 LATEST HACKATHON UPDATES & CRITICAL SAFETY GUARANTEES

✅ **Problem 1: Random answers & Hallucinations** -> **FIXED**
Banking facts (account number, balance, transactions) **ALWAYS come from JSON**, never from LLM hallucination.

✅ **Problem 2: Out of Scope "Ice Cream" Queries** -> **FIXED**
Strict banking domain constraint. If a user asks "how is ice cream made", the backend immediately intercepts it and returns a polite "It seems this question is not related to bank queries" in the correct locale without hitting the LLM.

✅ **Problem 3: Long TTS responses & UI Freezes** -> **FIXED**
New **STOP Audio** button renders when answering to instantly interrupt long TTS output. Re-rendered Voice Orb cleanly to eliminate white-screen crashes.

✅ **Problem 4: Conversation Momentum** -> **FIXED**
Added contextual Follow-Up Suggestion Chips dynamically generated based on previous questions (e.g. asking about balance recommends asking about transactions).

✅ **Problem 5: Data Privacy & True Offline AI** -> **FIXED**
Replaced external cloud endpoints (like Gemini/OpenAI) with a local Ollama integration running `qwen2.5:3b`. Zero user PII or financial data ever leaves the local machine!

## System Architecture

- **Banking facts layer:** Deterministic JSON lookup (account, balance, transactions, profile).
- **FAQ & Advanced Knowledge layer:** Vector search over embeddings powered by local ChromaDB & MiniLM.
- **NLP Shield Layer:** Fast Regex mapping to localized strings to bounce unverified domains.
- **Refinement layer:** Local offline LLM (Ollama / Qwen) for translating safely fetched JSON facts into natural, polite multilingual conversational text.
- **Interactive UI:** React + Vite modern dashboard with dynamic widgets, follow-up chips, and interrupt hooks.

## Technical Requirements & Stack

### Backend Stack
*   **Python + Flask:** Core API Server
*   **ChromaDB:** Local vectorized data storage for RAG
*   **Ollama (Qwen 2.5):** Localized LLM inference engine

### Frontend Stack
*   **React 18 + Vite:** Fast UI component framework
*   **Tailwind CSS:** Layout and animated UI effects
*   **Web Speech API:** In-browser Speech-To-Text processing

---

## Setup Instructions

### 1) Prerequisites
- Python 3.10+
- Node.js 18+
- [Ollama](https://ollama.com/) (Required for local LLM refinement)

### 2) Download Offline AI Models
Before starting the app, pull the required local language model for generation:
```bash
ollama pull qwen2.5:3b
```
*(Optionally, you can use `qwen2.5:1.5b` for even faster responses on lower-end hardware).*

### 3) Clone project
```bash
git clone https://github.com/Pranay9-coder/CodeApex_2.0.git
cd CodeApex_2.0
```

### 4) Python Backend Setup
```bash
python -m venv .venv

# Activate venv (Windows):
.venv\Scripts\activate

# Activate venv (Mac/Linux):
source .venv/bin/activate

pip install -r requirements.txt
```

### 5) Configuration (.env)
Create a new file named `.env` in the root directory `CodeApex_2.0/`.
Configure the local Ollama settings:
```env
OLLAMA_ENABLED=true
OLLAMA_MODEL=qwen2.5:3b
```

### 6) Re-Build Vector Embeddings 
*(Run after updating JSON data in `embeddings/data`)*
```bash
python embeddings/create_embeddings.py
```
This builds new semantic definitions and localizes text intents into the local ChromaDB store.

### 7) Run the Application

**Terminal 1 (Flask Backend):**
```bash
python app.py
```

**Terminal 2 (React Frontend):**
```bash
cd frontend
npm install
npm run dev
```

🔑 **Login:** Use Demo Phone Number `9000007124` to interact!
