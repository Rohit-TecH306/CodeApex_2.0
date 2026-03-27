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
Expanded vector database to interpret complex nested JSONs like dvanced_bank_knowledge.json for Home Loans, Eligibility, and Interest Rates out-of-the-box.

## System Architecture

- **Banking facts layer:** Deterministic JSON lookup (account, balance, transactions, profile).
- **FAQ & Advanced Knowledge layer:** Vector search over embeddings powered by ChromaDB.
- **NLP Shield Layer:** Fast Regex mapping to localized strings to bounce unverified domains.
- **Refinement layer:** Optional local Indic-LLaMA or Gemini for language polish only.
- **Interactive UI:** React + Vite modern dashboard with dynamically updating Follow-Up Prompts and Interrupt Hooks.

## Refinement Modes (Gemini vs Indic-LLaMA)

- **Gemini (recommended for hackathon demos):** Best speed/quality tradeoff. Assumes stable internet.
- **Indic-LLaMA-7B (optional):** local model path, better when you have strong GPU resources and want fully offline-ish control.

### Option A: Gemini setup (recommended)

1. Set environment variables:
   `ash
   export GEMINI_ENABLED="true"
   export GEMINI_API_KEY="YOUR_API_KEY"
   `
2. Start backend: python app.py

### Option B: Offline LLaMA setup (optional)

`ash
export GEMINI_ENABLED="false"
export INDIC_LLM_ENABLED="true"
python app.py
`

## Setup Instructions

### 1) Prerequisites
- Python 3.10+
- Node.js 18+

### 2) Clone project
`ash
git clone https://github.com/Pranay9-coder/CodeApex_2.0.git
cd CodeApex_2.0
`

### 3) Python Backend
`ash
python -m venv .venv
# Activate venv
pip install -r requirements.txt
`

### 4) Re-Build Vector Embeddings (Crucial after Data updates)
`ash
python embeddings/create_embeddings.py
`
This builds new definitions mapping localized text to intents, plus all nested logic from embeddings/data/advanced_bank_knowledge.json.

### 5) Run Backend + Frontend
**Terminal 1 (Flask):**
`ash
python app.py
`
**Terminal 2 (React):**
`ash
cd frontend
npm install
npm run dev
`

Use Demo Phone: 9000007124 to Login.

