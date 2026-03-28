# Embeddings Module

This module handles vector indexing and FAQ retrieval using local ChromaDB and `sentence-transformers`. It ensures complete offline data governance and RAG operations.

## Purpose
- Build internal embeddings from banking FAQ/data dictionaries (`data/*.json`).
- Retrieve semantically similar answers for real-time user queries.
- Connect deterministic logic securely to a local offline LLM (Ollama) to support multilingual response flow.

## Setup

First, install project-root Python environment requirements:
```bash
pip install -r requirements.txt
```

## Creating & Refreshing Embeddings 

Whenever you update JSON files in `embeddings/data/`, you must rebuild the local Vector database. From project root:
```bash
python embeddings/create_embeddings.py
```

*Vector store location is local: `embeddings/db/`*

## Offline LLM Refinement Setup (Ollama)

This search pipeline utilizes a localized LLM to rewrite, refine, and translate robotic database output into natural sounding Hindi, Marathi, and English. No external tokens or API Keys are used.

### Prerequisites
1. Download and install [Ollama](https://ollama.com/)
2. Open terminal and pull the local Qwen model:
   ```bash
   ollama pull qwen2.5:3b
   ```

### Configuration
Update the `.env` settings located in the project root before running the backend:

```env
OLLAMA_ENABLED=true
OLLAMA_MODEL=qwen2.5:3b
```

## Local Verification

After initiating the Python backend (`app.py`), you can verify the inference logic status by running the Flask server and checking the API endpoint:
- `/api/model-status`

You should see:
- `"configured_mode": "ollama"`
- `"ollama_enabled": "true"`
