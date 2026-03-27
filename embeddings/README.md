# Embeddings Module

This module handles vector indexing and FAQ retrieval using ChromaDB and sentence-transformers.

## Purpose
- Build embeddings from banking FAQ/data
- Retrieve semantically similar answers for user queries
- Support multilingual response flow with backend integration

## Setup

Use project root Python environment:
```bash
pip install -r requirements.txt
```

## Create/Refresh Embeddings

From project root:
```bash
python embeddings/create_embeddings.py
```

Vector store location:
- `embeddings/db/`

## Quick Check

Run backend and ask FAQ-style questions via `/api/chat` to validate retrieval.
