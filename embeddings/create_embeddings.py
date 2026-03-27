import json
from chromadb import PersistentClient
from sentence_transformers import SentenceTransformer

# 1) Embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")

# 2) Create persistent DB client
client = PersistentClient(path="./db")

# Delete old collection to avoid duplicate records
try:
    client.delete_collection("bank_data")
except Exception:
    pass

collection = client.get_or_create_collection(name="bank_data")

# 3) Load all JSON files
with open("../data/users.json", encoding="utf-8") as f:
    users = json.load(f)

with open("../data/accounts.json", encoding="utf-8") as f:
    accounts = json.load(f)

with open("../data/transactions.json", encoding="utf-8") as f:
    transactions = json.load(f)

with open("../data/general.json", encoding="utf-8") as f:
    faqs = json.load(f)

# 4) Build documents
records = []

for u in users:
    text = (
        f"User profile. User ID: {u['user_id']}. Name: {u['name']}. "
        f"District: {u['district']}. User type: {u['user_type']}. "
        f"Mobile: {u['mobile']}."
    )
    records.append(
        {
            "document": text,
            "metadata": {
                "type": "user",
                "user_id": u["user_id"],
                "language": "en",
            },
        }
    )

for a in accounts:
    text = (
        f"Account details. User ID: {a['user_id']}. "
        f"Account number: {a['account_number']}. "
        f"Account type: {a['account_type']}. Balance: {a['balance']} rupees."
    )
    records.append(
        {
            "document": text,
            "metadata": {
                "type": "account",
                "user_id": a["user_id"],
                "account_number": a["account_number"],
                "language": "en",
            },
        }
    )

for t in transactions:
    text = (
        f"Transaction history. Transaction ID: {t['transaction_id']}. "
        f"User ID: {t['user_id']}. Type: {t['type']}. Amount: {t['amount']} rupees. "
        f"Date: {t['date']}. Description: {t['description']}."
    )
    records.append(
        {
            "document": text,
            "metadata": {
                "type": "transaction",
                "user_id": t["user_id"],
                "transaction_id": t["transaction_id"],
                "txn_type": t["type"],
                "language": "en",
            },
        }
    )

for g in faqs:
    text = (
        f"FAQ. Question: {g['question']} "
        f"Answer: {g['answer']} "
        f"Intent: {g['intent']} "
        f"Language: {g['language']}"
    )
    records.append(
        {
            "document": text,
            "metadata": {
                "type": "faq",
                "intent": g["intent"],
                "language": g["language"],
            },
        }
    )

# 5) Encode and store
print("Generating embeddings...")

documents = [r["document"] for r in records]
metadatas = [r["metadata"] for r in records]
ids = [f"id_{i}" for i in range(len(records))]

embeddings = model.encode(documents).tolist()

collection.add(
    documents=documents,
    embeddings=embeddings,
    metadatas=metadatas,
    ids=ids,
)

print("Embeddings created and stored in ./db")
print("Total embeddings stored:", collection.count())
