import json
import io
import os
import unicodedata
from pathlib import Path
from contextlib import redirect_stderr, redirect_stdout
from typing import Dict, List, Optional, Tuple
import os
import google.generativeai as genai

from chromadb import PersistentClient
from sentence_transformers import SentenceTransformer

# 1) Load model and vector DB
# Resolve paths relative to this file so imports work from any working directory.
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_DIR = BASE_DIR / "db"

# Silence non-critical model load report text during startup.
with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
    model = SentenceTransformer("all-MiniLM-L6-v2")
client = PersistentClient(path=str(DB_DIR))
collection = client.get_collection(name="bank_data")

# 2) Load source JSON data
with open(DATA_DIR / "users.json", encoding="utf-8") as f:
    users = json.load(f)

with open(DATA_DIR / "accounts.json", encoding="utf-8") as f:
    accounts = json.load(f)

with open(DATA_DIR / "transactions.json", encoding="utf-8") as f:
    transactions = json.load(f)

with open(DATA_DIR / "general.json", encoding="utf-8") as f:
    faqs = json.load(f)

USER_BY_MOBILE: Dict[str, dict] = {u["mobile"]: u for u in users}
ACCOUNT_BY_USER: Dict[str, dict] = {a["user_id"]: a for a in accounts}
TXNS_BY_USER: Dict[str, List[dict]] = {}
for t in transactions:
    TXNS_BY_USER.setdefault(t["user_id"], []).append(t)

FAQ_BY_INTENT_LANG: Dict[Tuple[str, str], str] = {}
for f in faqs:
    FAQ_BY_INTENT_LANG[(f["intent"], f["language"])] = f["answer"]

# FAQ confidence guardrails.
MAX_FAQ_DISTANCE = 0.95
MIN_FAQ_DISTANCE_GAP = 0.08

# Optional Gemini refinement (recommended for faster multilingual quality).
GEMINI_ENABLED = os.getenv("GEMINI_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

# Optional local Indic LLM refinement (disabled by default).
INDIC_LLM_ENABLED = os.getenv("INDIC_LLM_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
INDIC_LLM_MODEL_NAME = os.getenv("INDIC_LLM_MODEL", "ai4bharat/Indic-LLaMA-7B")
INDIC_LLM_DEVICE = os.getenv("INDIC_LLM_DEVICE", "cpu")  # Use "cuda" if GPU available

# Lazy-load Indic model to avoid startup delay if not needed.
_indic_model = None
_indic_tokenizer = None
_indic_model_load_error = None
_gemini_model = None
_gemini_model_load_error = None
_last_refiner = "deterministic"


def _lazy_load_gemini_model():
    """Load Gemini client on first use with fallback."""
    global _gemini_model, _gemini_model_load_error

    if _gemini_model is not None or _gemini_model_load_error is not None:
        return _gemini_model

    if not GEMINI_ENABLED:
        _gemini_model_load_error = "Gemini disabled"
        return None
    if not GEMINI_API_KEY:
        _gemini_model_load_error = "GEMINI_API_KEY missing"
        return None

    try:
        import google.generativeai as genai  # type: ignore[import-not-found]

        genai.configure(api_key=GEMINI_API_KEY)
        _gemini_model = genai.GenerativeModel(GEMINI_MODEL)
        return _gemini_model
    except Exception as e:
        _gemini_model_load_error = str(e)
        print(f"Warning: Could not load Gemini model: {e}. Using fallback responses.")
        return None


def _pick_torch_device() -> str:
    try:
        import torch

        if INDIC_LLM_DEVICE == "cuda" and torch.cuda.is_available():
            return "cuda"
    except Exception:
        pass
    return "cpu"


def _lazy_load_indic_model():
    """Load Indic-LLaMA model on first use with fallback."""
    global _indic_model, _indic_tokenizer, _indic_model_load_error
    
    if _indic_model is not None or _indic_model_load_error is not None:
        return _indic_model, _indic_tokenizer
    
    try:
        if not INDIC_LLM_ENABLED:
            _indic_model_load_error = "Indic LLM disabled"
            return None, None
        
        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM
        except ImportError:
            _indic_model_load_error = "transformers not installed"
            return None, None
        
        device = _pick_torch_device()
        
        print(f"Loading Indic-LLaMA model ({INDIC_LLM_MODEL_NAME}) on {device}...")
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            _indic_tokenizer = AutoTokenizer.from_pretrained(INDIC_LLM_MODEL_NAME)
            _indic_model = AutoModelForCausalLM.from_pretrained(INDIC_LLM_MODEL_NAME)

        # Move model to selected device after load for broad compatibility.
        try:
            _indic_model = _indic_model.to(device)
        except Exception:
            # Keep CPU if transfer is not possible in this environment.
            device = "cpu"
            _indic_model = _indic_model.to(device)

        _indic_model = _indic_model.eval()
        print(f"Indic-LLaMA loaded successfully on {device}")
        return _indic_model, _indic_tokenizer
    except Exception as e:
        _indic_model_load_error = str(e)
        print(f"Warning: Could not load Indic-LLaMA model: {e}. Using fallback responses.")
        return None, None


def normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", text).lower().strip()


def print_help_examples() -> None:
    print("\nSample questions you can ask:")
    print("English:")
    print("- What is my current account balance?")
    print("- Show my last five transactions with dates.")
    print("- What is my account number and account type?")
    print("- Tell me my name, district, and user category.")
    print("- Is my account active right now?")
    print("- How do I update KYC and reset UPI PIN?")
    print("- What is the current loan interest information?")
    print("Hindi:")
    print("- मेरे खाते में अभी कितना बैलेंस है?")
    print("- मेरे पिछले पांच लेनदेन तारीख के साथ दिखाओ।")
    print("- मेरा अकाउंट नंबर और अकाउंट टाइप बताओ।")
    print("- मेरा नाम, जिला और यूज़र प्रकार बताओ।")
    print("- क्या मेरा खाता सक्रिय है?")
    print("- KYC अपडेट और UPI PIN रीसेट कैसे करें?")
    print("- लोन पर ब्याज की जानकारी क्या है?")
    print("Marathi:")
    print("- माझ्या खात्यात आत्ता किती शिल्लक आहे?")
    print("- माझे शेवटचे पाच व्यवहार तारखेसह दाखवा.")
    print("- माझा खाते क्रमांक आणि खाते प्रकार सांगा.")
    print("- माझे नाव, जिल्हा आणि वापरकर्ता प्रकार सांगा.")
    print("- माझे खाते सक्रिय आहे का?")
    print("- KYC अपडेट आणि UPI PIN रीसेट कसे करायचे?")
    print("- कर्जावरील व्याजाची माहिती काय आहे?")
    print("Type 'help' anytime to see this list again.\n")


def detect_language(text: str) -> str:
    q = normalize(text)

    marathi_markers = [
        "माझ", "शिल्लक", "काय", "कसे", "आहे", "करायचे", "साठी", "व्याज", "कर्ज",
    ]
    hindi_markers = [
        "मेरे", "मेरा", "कैसे", "कितना", "है", "करें", "चाहिए", "लोन", "ब्याज",
    ]

    has_devanagari = any("\u0900" <= ch <= "\u097f" for ch in text)
    if has_devanagari:
        mr_hits = sum(1 for m in marathi_markers if m in q)
        hi_hits = sum(1 for m in hindi_markers if m in q)
        return "mr" if mr_hits >= hi_hits else "hi"

    # Romanized query hints for Hindi/Marathi typed in Latin script.
    roman_hi_markers = ["mera", "mere", "kaise", "kya", "len den", "khata", "byaaj"]
    roman_mr_markers = ["majha", "majhe", "kase", "kay", "khate", "shillak", "vyavhar", "karayche"]
    hi_hits = sum(1 for m in roman_hi_markers if m in q)
    mr_hits = sum(1 for m in roman_mr_markers if m in q)
    if hi_hits or mr_hits:
        return "mr" if mr_hits > hi_hits else "hi"

    return "en"


def detect_intent(query: str) -> str:
    q = normalize(query)

    if any(word in q for word in [
        "balance", "बैलेंस", "बॅलन्स", "शिल्लक", "पैसा", "पैसे", "money", "funds",
        "available amount", "available funds", "khate me kitna", "khatyat kiti", "saldo",
    ]):
        return "account_balance"

    if any(word in q for word in [
        "transaction",
        "transactions",
        "last transaction",
        "last transactions",
        "recent transaction",
        "recent transactions",
        "history",
        "statement",
        "mini statement",
        "लेनदेन",
        "व्यवहार",
        "ट्रांजैक्शन",
        "मिनी स्टेटमेंट",
        "स्टेटमेंट",
        "len den",
        "vyavhar",
        "vyavhaar",
    ]):
        return "transactions"

    if any(word in q for word in [
        "account number",
        "account no",
        "a/c number",
        "ac number",
        "खाता नंबर",
        "खाते क्रमांक",
        "खाते नंबर",
        "मेरा अकाउंट नंबर",
        "अकाउंट नंबर",
        "khata number",
        "khate kramank",
        "khate number",
        "mera account number",
        "account type",
        "खाता प्रकार",
        "खाते प्रकार",
        "खाते का प्रकार",
        "khata prakar",
        "khate prakar",
    ]):
        return "account_details"

    if any(word in q for word in [
        "account active",
        "account status",
        "is my account active",
        "is account active",
        "खाता सक्रिय",
        "खाता चालू",
        "खाते सक्रिय",
        "खाते चालू",
        "status",
    ]):
        return "account_status"

    if any(word in q for word in [
        "my name",
        "tell my name",
        "what is my name",
        "what is my district",
        "tell my district",
        "which district",
        "where do i live",
        "who am i",
        "mera naam",
        "mera name",
        "mera jila",
        "mera district",
        "mujhe mera naam batao",
        "majha nav",
        "majhe nav",
        "maje nav",
        "nav sanga",
        "majha jilha",
        "majha district",
        "my profile",
        "मेरा नाम",
        "मेरे नाम",
        "मेरा जिला",
        "मेरा प्रोफाइल",
        "मुझे मेरा नाम बताओ",
        "मेरा प्रोफाइल",
        "माझे नाव",
        "माझं नाव",
        "माझा जिल्हा",
        "माझे प्रोफाइल",
        "माझे प्रोफाइल",
        "district",
        "जिला",
        "जिल्हा",
        "user type",
        "वापरकर्ता",
    ]):
        return "user_profile"

    if any(word in q for word in ["loan", "कर्ज", "लोन", "interest", "interest rate", "ब्याज", "व्याज", "byaaj", "vyaj"]):
        return "loan_query"

    if any(word in q for word in ["kyc", "केवाईसी", "केवायसी", "केवायसी", "k y c"]):
        return "kyc_update"

    return "general"


def is_bank_related(query: str) -> bool:
    q = normalize(query)
    keywords = [
        "bank", "account", "balance", "transaction", "loan", "kyc", "atm", "card", "upi", "neft", "rtgs",
        "बैंक", "खाता", "बैलेंस", "लेनदेन", "लोन", "कार्ड", "पैसा", "केवाईसी",
        "बँक", "खाते", "शिल्लक", "व्यवहार", "कर्ज", "कार्ड", "पैसे",
        "mini statement", "statement", "status", "active", "interest", "pin",
        "khata", "khate", "len den", "vyavhar", "karj", "byaaj", "upy",
        "name", "profile", "district", "mera naam", "majha nav", "majhe nav", "nav",
    ]
    return any(k in q for k in keywords)

def unrelated_message(lang: str) -> str:
    messages = {
        "en": "It seems this question is not related to the bank queries.",
        "hi": "ऐसा लगता है कि यह प्रश्न बैंक से संबंधित नहीं है।",
        "mr": "असे दिसते की हा प्रश्न बँकेंशी संबंधित नाही."
    }
    return messages.get(lang, messages["en"])

def handoff_message(lang: str) -> str:
    messages = {
        "en": "I am not fully confident about this answer. I will connect you to a bank officer.",
        "hi": "मुझे इस उत्तर पर पूरा भरोसा नहीं है। मैं आपको बैंक अधिकारी से जोड़ता हूँ।",
        "mr": "या उत्तराबद्दल मला पूर्ण खात्री नाही. मी तुम्हाला बँक अधिकाऱ्याशी जोडतो.",
    }
    return messages.get(lang, messages["en"])


def out_of_scope_message(lang: str) -> str:
    messages = {
        "en": (
            "I can currently help with banking topics only, such as balance, transactions, account details, "
            "KYC, and loan information. For other topics, please contact a bank officer."
        ),
        "hi": (
            "मैं अभी केवल बैंकिंग विषयों में मदद कर सकता हूँ, जैसे बैलेंस, लेनदेन, खाता विवरण, "
            "KYC और लोन जानकारी। अन्य विषयों के लिए कृपया बैंक अधिकारी से संपर्क करें।"
        ),
        "mr": (
            "मी सध्या फक्त बँकिंग विषयांमध्ये मदत करू शकतो, जसे शिल्लक, व्यवहार, खाते तपशील, "
            "KYC आणि कर्ज माहिती. इतर विषयांसाठी कृपया बँक अधिकाऱ्याशी संपर्क करा."
        ),
    }
    return messages.get(lang, messages["en"])


def uncertain_faq_message(lang: str) -> str:
    messages = {
        "en": (
            "I could not find a reliable answer to that banking question. "
            "Please rephrase your question, or I can connect you to a bank officer."
        ),
        "hi": (
            "मुझे इस बैंकिंग प्रश्न का विश्वसनीय उत्तर नहीं मिला। "
            "कृपया प्रश्न दोबारा लिखें, या मैं आपको बैंक अधिकारी से जोड़ सकता हूँ।"
        ),
        "mr": (
            "या बँकिंग प्रश्नासाठी मला विश्वासार्ह उत्तर मिळाले नाही. "
            "कृपया प्रश्न पुन्हा विचारा, किंवा मी तुम्हाला बँक अधिकाऱ्याशी जोडू शकतो."
        ),
    }
    return messages.get(lang, messages["en"])


def _maybe_refine_with_indic_model(query: str, answer: str, lang: str) -> str:
    """Optionally improve phrasing using Indic-LLaMA while keeping facts unchanged."""
    if not INDIC_LLM_ENABLED:
        return answer
    
    model, tokenizer = _lazy_load_indic_model()
    if model is None or tokenizer is None:
        return answer

    # Keep escalation/scope messages deterministic and policy-safe.
    protected = {
        handoff_message(lang),
        out_of_scope_message(lang),
        uncertain_faq_message(lang),
    }
    if answer in protected:
        return answer

    language_name = {"en": "English", "hi": "Hindi", "mr": "Marathi"}.get(lang, "English")
    prompt = (
        f"You are a banking response refiner. Target language: {language_name}.\n"
        "Rules:\n"
        "1) Keep all numbers, dates, amounts and account identifiers unchanged.\n"
        "2) Do not add new facts, policy claims, or advice.\n"
        "3) Keep response concise and natural.\n"
        "4) Return only the refined answer text.\n\n"
        f"User question: {query}\n"
        f"Base answer: {answer}"
    )

    try:
        import torch
        inputs = tokenizer(prompt, return_tensors="pt", max_length=768, truncation=True)
        if _pick_torch_device() == "cuda" and torch.cuda.is_available():
            inputs = {k: v.cuda() for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=120,
                temperature=0.2,
                top_p=0.9,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )
        
        generated_tokens = outputs[0][inputs["input_ids"].shape[1]:]
        candidate = tokenizer.decode(generated_tokens, skip_special_tokens=True).strip()
        return candidate[:500].strip() or answer
    except Exception:
        return answer


def _maybe_refine_with_gemini(query: str, answer: str, lang: str) -> str:
    """Optionally improve phrasing using Gemini while keeping facts unchanged."""
    model = _lazy_load_gemini_model()
    if model is None:
        return answer

    protected = {
        handoff_message(lang),
        out_of_scope_message(lang),
        uncertain_faq_message(lang),
    }
    if answer in protected:
        return answer

    language_name = {"en": "English", "hi": "Hindi", "mr": "Marathi"}.get(lang, "English")
    prompt = (
        f"You are a banking response refiner. Target language: {language_name}.\n"
        "Rules:\n"
        "1) Keep all numbers, amounts, dates, account identifiers and facts exactly unchanged.\n"
        "2) Do not add new facts, policies, or advice.\n"
        "3) Keep the response concise and user-friendly.\n"
        "4) Return only the final refined answer text.\n\n"
        f"User question: {query}\n"
        f"Base answer: {answer}"
    )

    try:
        response = model.generate_content(prompt)
        candidate = (getattr(response, "text", "") or "").strip()
        if not candidate:
            return answer
        return candidate[:500]
    except Exception:
        return answer


def refine_answer(query: str, answer: str, lang: str) -> str:
    """Refine answer with Gemini first, then Indic model fallback."""
    global _last_refiner
    refined = _maybe_refine_with_gemini(query, answer, lang)
    if refined != answer:
        _last_refiner = "gemini"
        return refined

    refined = _maybe_refine_with_indic_model(query, answer, lang)
    if refined != answer:
        _last_refiner = "indic-llama"
        return refined

    _last_refiner = "deterministic"
    return answer


def get_refiner_status() -> Dict[str, str]:
    """Return active and configured refinement backend details."""
    configured = "deterministic"
    if GEMINI_ENABLED and GEMINI_API_KEY:
        configured = "gemini"
    elif INDIC_LLM_ENABLED:
        configured = "indic-llama"

    return {
        "configured_mode": configured,
        "last_used_mode": _last_refiner,
        "gemini_enabled": str(GEMINI_ENABLED).lower(),
        "indic_enabled": str(INDIC_LLM_ENABLED).lower(),
    }


# User-specific answers (deterministic)
def format_currency(amount: int) -> str:
    return f"{amount:,}"


def get_balance(user_id: str, lang: str) -> str:
    acc = ACCOUNT_BY_USER.get(user_id)
    if not acc:
        return {
            "en": "Account not found.",
            "hi": "खाता नहीं मिला।",
            "mr": "खातेची माहिती सापडली नाही.",
        }[lang]

    bal = format_currency(acc["balance"])
    if lang == "hi":
        return f"आपके खाते में ₹{bal} बैलेंस है।"
    if lang == "mr":
        return f"तुमच्या खात्यात ₹{bal} शिल्लक आहे."
    return f"Your account balance is ₹{bal}."


def get_transactions(user_id: str, lang: str, limit: int = 5) -> str:
    rows = sorted(TXNS_BY_USER.get(user_id, []), key=lambda x: x["date"], reverse=True)[:limit]
    if not rows:
        return {
            "en": "No transactions found.",
            "hi": "कोई लेनदेन नहीं मिला।",
            "mr": "व्यवहार सापडले नाहीत.",
        }[lang]

    if lang == "hi":
        header = "आपके हाल के लेनदेन:"
        line = "- {date}: {typ} ₹{amt}"
        credit_label = "जमा"
        debit_label = "निकासी"
    elif lang == "mr":
        header = "तुमचे अलीकडील व्यवहार:"
        line = "- {date}: {typ} ₹{amt}"
        credit_label = "जमा"
        debit_label = "डेबिट"
    else:
        header = "Your recent transactions:"
        line = "- {date}: {typ} ₹{amt}"
        credit_label = "credit"
        debit_label = "debit"

    lines = [header]
    for r in rows:
        typ = credit_label if r["type"].lower() == "credit" else debit_label
        lines.append(line.format(date=r["date"], typ=typ, amt=format_currency(r["amount"])))
    return "\n".join(lines)


def get_account_details(user_id: str, lang: str) -> str:
    acc = ACCOUNT_BY_USER.get(user_id)
    if not acc:
        return {
            "en": "Account details not found.",
            "hi": "खाते का विवरण नहीं मिला।",
            "mr": "खातेचे तपशील सापडले नाहीत.",
        }[lang]

    if lang == "hi":
        return (
            f"आपका अकाउंट नंबर {acc['account_number']} है। "
            f"अकाउंट प्रकार: {acc['account_type']}।"
        )
    if lang == "mr":
        return (
            f"तुमचा खाते क्रमांक {acc['account_number']} आहे. "
            f"खाते प्रकार: {acc['account_type']}."
        )
    return (
        f"Your account number is {acc['account_number']}. "
        f"Account type: {acc['account_type']}."
    )


def get_user_profile(user: dict, lang: str) -> str:
    if lang == "hi":
        return (
            f"आपका नाम {user['name']} है। "
            f"जिला: {user['district']}। "
            f"यूज़र प्रकार: {user['user_type']}।"
        )
    if lang == "mr":
        return (
            f"तुमचे नाव {user['name']} आहे. "
            f"जिल्हा: {user['district']}. "
            f"वापरकर्ता प्रकार: {user['user_type']}."
        )
    return (
        f"Your name is {user['name']}. "
        f"District: {user['district']}. "
        f"User type: {user['user_type']}."
    )


def get_account_status(lang: str) -> str:
    if lang == "hi":
        return "आपका खाता सक्रिय है।"
    if lang == "mr":
        return "तुमचे खाते सक्रिय आहे."
    return "Your account is active."


# FAQ retrieval with confidence guardrail

def extract_answer(doc: str) -> str:
    if "Answer:" in doc:
        start = doc.find("Answer:") + len("Answer:")
        end = doc.find("Intent:")
        if end == -1:
            return doc[start:].strip()
        return doc[start:end].strip()
    return doc.strip()


def vector_search_faq(query: str, lang: str) -> str:
    query_embedding = model.encode([query]).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=6,
        where={"type": "faq"},
        include=["documents", "metadatas", "distances"],
    )

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    if not docs:
        return uncertain_faq_message(lang)

    top_dist = distances[0] if distances else 999.0
    if top_dist > MAX_FAQ_DISTANCE:
        return uncertain_faq_message(lang)

    # If top candidates are too close but represent different intents, avoid random answer.
    if len(distances) > 1 and len(metas) > 1:
        gap = distances[1] - distances[0]
        top_intent = metas[0].get("intent")
        second_intent = metas[1].get("intent")
        if top_intent != second_intent and gap < MIN_FAQ_DISTANCE_GAP:
            return uncertain_faq_message(lang)

    # Prefer same-language answer with good distance.
    for doc, meta, dist in zip(docs, metas, distances):
        if meta.get("language") == lang and dist <= MAX_FAQ_DISTANCE:
            return refine_answer(query, extract_answer(doc), lang)

    # Fallback 1: best intent in requested language.
    top_intent = metas[0].get("intent") if metas else None
    top_dist = distances[0] if distances else 999.0
    if top_intent and (top_intent, lang) in FAQ_BY_INTENT_LANG and top_dist <= MAX_FAQ_DISTANCE:
        return refine_answer(query, FAQ_BY_INTENT_LANG[(top_intent, lang)], lang)

    # Fallback 2: strict language query.
    lang_results = collection.query(
        query_embeddings=query_embedding,
        n_results=1,
        where={"$and": [{"type": "faq"}, {"language": lang}]},
        include=["documents", "distances"],
    )
    lang_docs = lang_results.get("documents", [[]])[0]
    lang_distances = lang_results.get("distances", [[]])[0]
    if lang_docs and lang_distances and lang_distances[0] <= MAX_FAQ_DISTANCE:
        return refine_answer(query, extract_answer(lang_docs[0]), lang)

    return uncertain_faq_message(lang)


def enhance_response_with_gemini(raw_answer: str, user_name: str, lang: str) -> str:
    """Uses Gemini to refine the raw technical response into an impressive natural language output."""
    lang_names = {"en": "English", "hi": "Hindi", "mr": "Marathi"}
    language_name = lang_names.get(lang, "English")

    system_prompt = f"""You are a polite and highly efficient AI Banking Assistant.
Your task is to rewrite the provided raw system response into a very short, clear, and direct statement.
- Maximum 1-2 sentences ONLY.
- Always use the exact data provided (don't makeup balances or dates).
- Do not include any greeting fillers like "I hope you are doing well" or sign-offs.
- Address the user briefly by name ({user_name}).
- MUST respond directly in {language_name}.
"""

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not found in environment. Returning raw answer.")
        return raw_answer

    genai.configure(api_key=api_key)

    try:
        model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=system_prompt)
        response = model.generate_content(
            f"Raw response to rewrite: '{raw_answer}'",
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
            )
        )
        return response.text.strip()
    except Exception as e:
        print(f"Gemini enhancement failed: {e}")
        return raw_answer


def answer_query(user: dict, query: str, lang_hint: Optional[str] = None) -> str:
    lang = lang_hint if lang_hint in {"en", "hi", "mr"} else detect_language(query)
    intent = detect_intent(query)
    user_id = user["user_id"]

    raw_answer = ""
    # Deterministic intents should be answered directly, even if keyword guard is weak.
    if intent == "account_balance":
        raw_answer = get_balance(user_id, lang)
    elif intent == "transactions":
        raw_answer = get_transactions(user_id, lang)
    elif intent == "account_details":
        raw_answer = get_account_details(user_id, lang)
    elif intent == "account_status":
        raw_answer = get_account_status(lang)
    elif intent == "user_profile":
        raw_answer = get_user_profile(user, lang)
    elif intent != "general":
        # For non-general intents (loan/kyc etc.), try FAQ retrieval directly.
        raw_answer = vector_search_faq(query, lang)
    elif not is_bank_related(query):
        raw_answer = unrelated_message(lang)
    else:
        raw_answer = vector_search_faq(query, lang)

    # Fast-pass handoff messages to skip rewriting
    if "officer" in raw_answer.lower() or "अधिकारी" in raw_answer or "not related" in raw_answer.lower() or "संबंधित नहीं" in raw_answer:
        return raw_answer

    # Apply Gemini rewrite
    return enhance_response_with_gemini(raw_answer, user.get("name", "User"), lang)


def run_cli() -> None:
    print("AI Banking Assistant started.")
    print("Supported languages: English, Hindi, Marathi")
    print("Use any valid mobile from data/users.json to login.")
    print("Example mobile: 9876543210")
    print("Type 'help' after login for sample questions.")

    mobile = input("Enter your mobile number: ").strip()
    user = USER_BY_MOBILE.get(mobile)

    if not user:
        print("User not found.")
        print("Try one of these demo numbers:")
        for m in list(USER_BY_MOBILE.keys())[:5]:
            print(f"- {m}")
        raise SystemExit(1)

    print("Login successful.")
    print_help_examples()

    while True:
        query = input("Ask your question (or type 'exit'): ").strip()
        if not query:
            continue
        if query.lower() == "help":
            print_help_examples()
            continue
        if query.lower() == "exit":
            print("Goodbye!")
            break

        answer = answer_query(user, query)
        print("\nAnswer:")
        print(answer)
        print("-" * 50)


if __name__ == "__main__":
    run_cli()
