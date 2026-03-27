# AI Bank Assistance - Domain-Safe Offline & Online Banking Assistant

## ?? LATEST HACKATHON UPDATES & CRITICAL SAFETY GUARANTEES

? **Problem 1: Random answers & Hallucinations** ? **FIXED**
Banking facts (account number, balance, transactions) **ALWAYS come from JSON**, never from LLM hallucination.

? **Problem 2: Out of Scope "Ice Cream" Queries** ? **FIXED**
Strict banking domain constraint. If a user asks "how is ice cream made", the backend immediately intercepts it and returns a polite "It seems this question is not related to bank queries" in the correct locale without hitting the LLM.

? **Problem 3: Long TTS responses & UI Freezes** ? **FIXED**
New **STOP Audio** button renders when answering to instantly interrupt long TTS output. Re-rendered Voice Orb cleanly to eliminate white-screen crashes.

? **Problem 4: Conversation Momentum** ? **FIXED**
Added contextual Follow-Up Suggestion Chips dynamically generated based on previous questions (e.g. asking about balance recommends asking about transactions).

? **Problem 5: Advanced Knowledge Processing** ? **FIXED**
Expanded vector database to interpret complex nested JSONs like \dvanced_bank_knowledge.json\ for Home Loans, Eligibility, and Interest Rates out-of-the-box.

## System Architecture

- **Banking facts layer:** Deterministic JSON lookup (account, balance, transactions, profile).
- **FAQ & Advanced Knowledge layer:** Vector search over embeddings powered by ChromaDB.
- **NLP Shield Layer:** Fast Regex mapping to localized strings to bounce unverified domains.
- **Refinement layer:** Optional local Indic-LLaMA or Gemini for language polish only.
- **Interactive UI:** React + Vite modern dashboard with dynamically updating Follow-Up Prompts and Interrupt Hooks.

## Setup Instructions

### 1) Prerequisites
- Python 3.10+
- Node.js 18+

### 2) Clone project
\\\ash
git clone https://github.com/Pranay9-coder/CodeApex_2.0.git
cd CodeApex_2.0
\\\

### 3) Python Backend Setup
\\\ash
python -m venv .venv
# Activate venv (Windows: .\\.venv\\Scripts\\Activate)
# Activate venv (Mac/Linux: source .venv/bin/activate)
pip install -r requirements.txt
\\\

### 4) Setup .env Configuration File (CRITICAL)
Create a new file named \.env\ in the root directory \CodeApex_2.0/\.
This file tells the system which AI model to use.

**Option A: Gemini setup (recommended for hackathon demos)**
\\\env
# .env file
GEMINI_ENABLED=true
GEMINI_API_KEY=your_actual_gemini_api_key_here
INDIC_LLM_ENABLED=false
\\\

**Option B: Offline Indic-LLaMA setup (optional)**
\\\env
# .env file
GEMINI_ENABLED=false
INDIC_LLM_ENABLED=true
# Optional: Use "cuda" if you have an Nvidia GPU, otherwise "cpu"
INDIC_LLM_DEVICE=cpu
\\\

### 5) Re-Build Vector Embeddings (Run after updating JSON data)
\\\ash
python embeddings/create_embeddings.py
\\\
This builds new definitions mapping localized text to intents, plus all nested logic from \embeddings/data/advanced_bank_knowledge.json\.

### 6) Run Backend + Frontend
**Terminal 1 (Flask Backend):**
\\\ash
python app.py
\\\
**Terminal 2 (React Frontend):**
\\\ash
cd frontend
npm install
npm run dev
\\\

?? **Login:** Use Demo Phone Number \9000007124\ to interact!
