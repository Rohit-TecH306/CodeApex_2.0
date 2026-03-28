import json
import io
import os
import re
import unicodedata
from pathlib import Path
from contextlib import redirect_stderr, redirect_stdout
from typing import Dict, List, Optional, Tuple

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

extended_faq_path = DATA_DIR / "general_extended.json"
if extended_faq_path.exists():
    with open(extended_faq_path, encoding="utf-8") as f:
        extended_faqs = json.load(f)
    if isinstance(extended_faqs, list):
        faqs.extend(extended_faqs)

with open(DATA_DIR / "advanced_bank_knowledge.json", encoding="utf-8") as f:
    advanced_knowledge = json.load(f)

credit_profiles_path = DATA_DIR / "credit_profiles.json"
if credit_profiles_path.exists():
    with open(credit_profiles_path, encoding="utf-8") as f:
        credit_profiles = json.load(f)
else:
    credit_profiles = []

USER_BY_MOBILE: Dict[str, dict] = {u["mobile"]: u for u in users}
ACCOUNT_BY_USER: Dict[str, dict] = {a["user_id"]: a for a in accounts}
CREDIT_PROFILE_BY_USER: Dict[str, dict] = {c["user_id"]: c for c in credit_profiles}
TXNS_BY_USER: Dict[str, List[dict]] = {}
for t in transactions:
    TXNS_BY_USER.setdefault(t["user_id"], []).append(t)

FAQ_BY_INTENT_LANG: Dict[Tuple[str, str], str] = {}
for idx, f in enumerate(faqs):
    intent = str(f.get("intent", "")).strip().lower() if isinstance(f, dict) else ""
    language = str(f.get("language", "")).strip().lower() if isinstance(f, dict) else ""
    answer = str(f.get("answer", "")).strip() if isinstance(f, dict) else ""
    if not (intent and language and answer):
        # Skip malformed/non-FAQ records to keep startup resilient.
        continue
    FAQ_BY_INTENT_LANG[(intent, language)] = answer

# FAQ confidence guardrails.
MAX_FAQ_DISTANCE = 0.78
MIN_FAQ_DISTANCE_GAP = 0.06
MAX_KNOWLEDGE_DISTANCE = 0.82

# Optional Ollama refinement (recommended for local offline high quality).
OLLAMA_ENABLED = os.getenv("OLLAMA_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")

# Optional local Indic LLM refinement (disabled by default).
INDIC_LLM_ENABLED = os.getenv("INDIC_LLM_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
INDIC_LLM_MODEL_NAME = os.getenv("INDIC_LLM_MODEL", "ai4bharat/Indic-LLaMA-7B")
INDIC_LLM_DEVICE = os.getenv("INDIC_LLM_DEVICE", "cpu")  # Use "cuda" if GPU available

# Lazy-load Indic model to avoid startup delay if not needed.
_indic_model = None
_indic_tokenizer = None
_indic_model_load_error = None
_last_refiner = "deterministic"


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
    tokens = set(re.findall(r"[a-z0-9]+", q))

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

    if (
        "fd" in tokens
        or any(word in q for word in ["fixed deposit", "term deposit", "एफडी", "फिक्स्ड डिपॉजिट", "मुदत ठेव"])
    ):
        return "fd_rates"

    if (
        "rd" in tokens
        or any(word in q for word in ["recurring deposit", "रेकरिंग", "आरडी", "आवर्ती जमा"])
    ):
        return "rd_info"

    if any(word in q for word in ["block card", "debit card block", "lost card", "कार्ड ब्लॉक", "कार्ड हरवला", "कार्ड बंद"]):
        return "card_block"

    if any(word in q for word in ["cheque book", "checkbook", "चेकबुक", "चेक बुक", "चेकबुक कसे"]):
        return "cheque_book"

    if any(word in q for word in ["net banking", "mobile banking", "internet banking", "नेट बैंकिंग", "मोबाइल बैंकिंग", "नेट बँकिंग"]):
        return "net_banking"

    if any(word in q for word in ["atm pin", "reset pin", "change pin", "एटीएम पिन", "पिन रीसेट", "पिन बदला"]):
        return "atm_pin_reset"

    if any(word in q for word in ["nominee", "add nominee", "nomination", "नॉमिनी", "नामिनी", "नामनिर्देशित"]):
        return "nominee_update"

    if any(word in q for word in ["ifsc", "branch code", "branch timing", "working hours", "आईएफएससी", "शाखा", "ब्रांच टाइमिंग"]):
        return "branch_info"

    if any(word in q for word in ["chargeback", "dispute", "wrong debit", "refund", "गलत कटौती", "विवाद", "चुकीची डेबिट"]):
        return "transaction_dispute"

    return "general"


def is_bank_related(query: str) -> bool:
    q = normalize(query)
    keywords = [
        "bank", "account", "balance", "transaction", "loan", "kyc", "atm", "card", "upi", "neft", "rtgs",
        "yojana", "pmay", "awas", "kisan", "pradhan mantri", "scheme", "sukanya", "samriddhi", "ppf",
        "योजना", "आवास", "किसान", "प्रधानमंत्री",
        "बैंक", "खाता", "बैलेंस", "लेनदेन", "लोन", "कार्ड", "पैसा", "केवाईसी",
        "बँक", "खाते", "शिल्लक", "व्यवहार", "कर्ज", "कार्ड", "पैसे",
        "mini statement", "statement", "active", "interest", "pin",
        "emi", "eligibility", "scheme", "fixed deposit", "savings account", "interest rate",
        "fd", "rd", "debit card", "credit card", "block card", "cheque", "checkbook",
        "passbook", "ifsc", "branch", "working hours", "mobile banking", "net banking",
        "nominee", "chargeback", "dispute", "refund",
        "khata", "khate", "len den", "vyavhar", "karj", "byaaj", "upy",
        "name", "profile", "district", "mera naam", "majha nav", "majhe nav", "nav",
        "चेकबुक", "पासबुक", "नॉमिनी", "शाखा", "आईएफएससी", "कार्ड ब्लॉक", "पिन रीसेट",
        "चेकबुक", "नावनोंदणी", "नॉमिनी", "शाखा वेळ", "कार्ड", "परतावा",
    ]
    return any(k in q for k in keywords)


def looks_like_advanced_knowledge_query(query: str) -> bool:
    q = normalize(query)
    markers = [
        "home loan", "personal loan", "education loan", "loan", "interest", "interest rate",
        "emi", "eligibility", "documents", "processing fee", "tenure", "scheme",
        "fixed deposit", "fd", "savings account", "kisan credit", "pm awas",
        "लोन", "कर्ज", "ब्याज", "व्याज", "ईएमआई", "पात्रता", "योजना",
    ]
    return any(m in q for m in markers)

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


def _is_uncertain_response(answer: str, lang: str) -> bool:
    return answer.strip() == uncertain_faq_message(lang)


def faq_by_intent(intent: str, lang: str) -> Optional[str]:
    ans = FAQ_BY_INTENT_LANG.get((intent, lang))
    if ans:
        return ans
    return FAQ_BY_INTENT_LANG.get((intent, "en"))


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


def _maybe_refine_with_ollama(query: str, answer: str, lang: str) -> str:
    """Optionally improve phrasing using local Ollama model while keeping facts unchanged."""
    if not OLLAMA_ENABLED:
        return answer

    protected = {
        handoff_message(lang),
        out_of_scope_message(lang),
        uncertain_faq_message(lang),
    }
    if answer in protected:
        return answer

    language_name = {"en": "English", "hi": "Hindi", "mr": "Marathi"}.get(lang, "English")
    
    messages = [
        {"role": "system", "content": f"You are a helpful, polite banking assistant refiner. Target language: {language_name}. Rules:\n1) Keep all numbers, amounts, dates, account identifiers and facts exactly unchanged.\n2) Do not add new facts, policies, or advice.\n3) Keep the response concise and user-friendly.\n4) Return ONLY the final refined answer text with no conversational filler like 'Here is the refined response'."},
        {"role": "user", "content": f"User question: {query}\nBase answer: {answer}"}
    ]

    try:
        import ollama
        response = ollama.chat(model=OLLAMA_MODEL, messages=messages)
        candidate = response.get("message", {}).get("content", "").strip()
        
        if not candidate:
            return answer
        return candidate[:500]
    except Exception as e:
        print(f"Ollama refinement failed: {e}")
        return answer


def refine_answer(query: str, answer: str, lang: str) -> str:
    """Refine answer with Ollama first, then Indic model fallback."""
    global _last_refiner
    refined = _maybe_refine_with_ollama(query, answer, lang)
    if refined != answer:
        _last_refiner = "ollama"
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
    if OLLAMA_ENABLED:
        configured = "ollama"
    elif INDIC_LLM_ENABLED:
        configured = "indic-llama"

    return {
        "configured_mode": configured,
        "last_used_mode": _last_refiner,
        "ollama_enabled": str(OLLAMA_ENABLED).lower(),
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


def extract_knowledge_info(doc: str) -> str:
    if "Information:" in doc:
        return doc.split("Information:", 1)[1].strip()
    return doc.strip()


def vector_search_knowledge(query: str, lang: str) -> str:
    query_embedding = model.encode([query]).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=3,
        where={"type": "advanced_knowledge"},
        include=["documents", "distances"],
    )

    docs = results.get("documents", [[]])[0]
    distances = results.get("distances", [[]])[0]

    if not docs or not distances:
        return uncertain_faq_message(lang)

    if distances[0] > MAX_KNOWLEDGE_DISTANCE:
        return uncertain_faq_message(lang)

    info = extract_knowledge_info(docs[0])
    if lang == "hi":
        base = f"उपलब्ध बैंक जानकारी: {info}"
    elif lang == "mr":
        base = f"उपलब्ध बँक माहिती: {info}"
    else:
        base = f"Available bank information: {info}"

    return refine_answer(query, base[:600], lang)


def _choose_loan_type(query: str) -> str:
    q = normalize(query)
    if any(k in q for k in ["personal", "पर्सनल", "वैयक्तिक"]):
        return "personal_loan"
    if any(k in q for k in ["education", "student", "शिक्षण", "एजुकेशन"]):
        return "education_loan"
    return "home_loan"


def get_advanced_knowledge_answer(query: str, lang: str) -> Optional[str]:
    q = normalize(query)

    if any(k in q for k in ["loan", "home loan", "personal loan", "education loan", "कर्ज", "लोन"]):
        loans = advanced_knowledge.get("loans", {})
        loan_key = _choose_loan_type(query)
        details = loans.get(loan_key, {})
        if not details:
            return None

        interest = details.get("interest_rate", "N/A")
        if isinstance(interest, dict):
            interest = ", ".join(f"{k}: {v}" for k, v in interest.items())
        eligibility = details.get("eligibility", {})
        income = eligibility.get("minimum_income", "N/A") if isinstance(eligibility, dict) else "N/A"
        credit = eligibility.get("credit_score", "N/A") if isinstance(eligibility, dict) else "N/A"

        if lang == "hi":
            return (
                f"{loan_key.replace('_', ' ').title()} के लिए ब्याज दर: {interest}. "
                f"न्यूनतम आय: {income}. पसंदीदा क्रेडिट स्कोर: {credit}."
            )
        if lang == "mr":
            return (
                f"{loan_key.replace('_', ' ').title()} साठी व्याजदर: {interest}. "
                f"किमान उत्पन्न: {income}. प्राधान्य क्रेडिट स्कोर: {credit}."
            )
        return (
            f"Interest rate for {loan_key.replace('_', ' ')}: {interest}. "
            f"Minimum income: {income}. Preferred credit score: {credit}."
        )

    if any(k in q for k in ["fixed deposit", "fd", "savings", "interest rate", "व्याजदर", "ब्याज दर"]):
        rates = advanced_knowledge.get("interest_rates", {})
        savings = rates.get("savings_account", "N/A")
        fd = rates.get("fixed_deposit", {})
        one_year = fd.get("1_year", "N/A") if isinstance(fd, dict) else "N/A"
        five_year = fd.get("5_year", "N/A") if isinstance(fd, dict) else "N/A"

        if lang == "hi":
            return (
                f"सेविंग्स अकाउंट दर: {savings}. "
                f"FD 1 वर्ष: {one_year}, FD 5 वर्ष: {five_year}."
            )
        if lang == "mr":
            return (
                f"सेव्हिंग्स खाते दर: {savings}. "
                f"FD 1 वर्ष: {one_year}, FD 5 वर्ष: {five_year}."
            )
        return (
            f"Savings account rate: {savings}. "
            f"FD 1 year: {one_year}, FD 5 year: {five_year}."
        )

    if any(k in q for k in ["scheme", "yojana", "योजना"]):
        schemes = advanced_knowledge.get("schemes", {})
        if not schemes:
            return None
        names = ", ".join(schemes.keys())
        if lang == "hi":
            return f"उपलब्ध योजनाएं: {names}."
        if lang == "mr":
            return f"उपलब्ध योजना: {names}."
        return f"Available schemes: {names}."

    return None


def enhance_response_with_ollama(raw_answer: str, user_name: str, lang: str) -> str:
    """Compatibility wrapper that routes to the configured refiner backend."""
    _ = user_name
    return refine_answer("", raw_answer, lang)


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
    elif intent in {"kyc_update", "loan_query"}:
        deterministic_knowledge = get_advanced_knowledge_answer(query, lang)
        if deterministic_knowledge:
            raw_answer = deterministic_knowledge
        elif looks_like_advanced_knowledge_query(query):
            raw_answer = vector_search_knowledge(query, lang)
            if _is_uncertain_response(raw_answer, lang):
                catalog_answer = faq_by_intent(intent, lang)
                if catalog_answer:
                    raw_answer = catalog_answer
                else:
                    raw_answer = vector_search_faq(query, lang)
        else:
            catalog_answer = faq_by_intent(intent, lang)
            if catalog_answer:
                raw_answer = catalog_answer
            else:
                raw_answer = vector_search_faq(query, lang)
    elif intent != "general":
        # Prefer deterministic intent-language FAQ when available.
        catalog_answer = faq_by_intent(intent, lang)
        if catalog_answer:
            raw_answer = catalog_answer
        else:
            raw_answer = vector_search_faq(query, lang)
    elif not is_bank_related(query):
        raw_answer = unrelated_message(lang)
    else:
        raw_answer = vector_search_faq(query, lang)
        if _is_uncertain_response(raw_answer, lang) and looks_like_advanced_knowledge_query(query):
            deterministic_knowledge = get_advanced_knowledge_answer(query, lang)
            if deterministic_knowledge:
                raw_answer = deterministic_knowledge
            else:
                raw_answer = vector_search_knowledge(query, lang)

    # Fast-pass handoff messages to skip rewriting
    if "officer" in raw_answer.lower() or "अधिकारी" in raw_answer or "not related" in raw_answer.lower() or "संबंधित नहीं" in raw_answer:
        return raw_answer

    # Apply Ollama rewrite
    return enhance_response_with_ollama(raw_answer, user.get("name", "User"), lang)


def get_follow_up_suggestions(query: str, lang_hint: Optional[str] = None) -> List[str]:
    """Return exactly three smart follow-up questions in the user's language."""
    lang = lang_hint if lang_hint in {"en", "hi", "mr"} else detect_language(query)
    intent = detect_intent(query)

    followups = {
        "en": {
            "account_balance": [
                "Show last 5 transactions",
                "Check FD rates",
                "Show EMI for 20 lakh loan",
            ],
            "transactions": [
                "What is my current balance?",
                "Show account details",
                "Check FD rates",
            ],
            "account_details": [
                "Is my account active?",
                "Show last 5 transactions",
                "Check FD rates",
            ],
            "loan_query": [
                "Show EMI for 20 lakh loan",
                "Check FD rates",
                "What is my current balance?",
            ],
            "general": [
                "Show last 5 transactions",
                "Check FD rates",
                "Show EMI for 20 lakh loan",
            ],
        },
        "hi": {
            "account_balance": [
                "पिछले 5 लेनदेन दिखाओ",
                "FD की ब्याज दर बताओ",
                "20 लाख लोन की EMI बताओ",
            ],
            "transactions": [
                "मेरा वर्तमान बैलेंस बताओ",
                "मेरा खाता विवरण दिखाओ",
                "FD की ब्याज दर बताओ",
            ],
            "account_details": [
                "क्या मेरा खाता सक्रिय है?",
                "पिछले 5 लेनदेन दिखाओ",
                "FD की ब्याज दर बताओ",
            ],
            "loan_query": [
                "20 लाख लोन की EMI बताओ",
                "होम लोन ब्याज दर क्या है?",
                "FD की ब्याज दर बताओ",
            ],
            "general": [
                "पिछले 5 लेनदेन दिखाओ",
                "FD की ब्याज दर बताओ",
                "20 लाख लोन की EMI बताओ",
            ],
        },
        "mr": {
            "account_balance": [
                "माझे शेवटचे 5 व्यवहार दाखवा",
                "FD चे व्याजदर तपासा",
                "20 लाख कर्जाची EMI दाखवा",
            ],
            "transactions": [
                "माझी सध्याची शिल्लक सांगा",
                "माझे खाते तपशील दाखवा",
                "FD चे व्याजदर तपासा",
            ],
            "account_details": [
                "माझे खाते सक्रिय आहे का?",
                "माझे शेवटचे 5 व्यवहार दाखवा",
                "FD चे व्याजदर तपासा",
            ],
            "loan_query": [
                "20 लाख कर्जाची EMI दाखवा",
                "होम लोन व्याजदर किती आहे?",
                "FD चे व्याजदर तपासा",
            ],
            "general": [
                "माझे शेवटचे 5 व्यवहार दाखवा",
                "FD चे व्याजदर तपासा",
                "20 लाख कर्जाची EMI दाखवा",
            ],
        },
    }

    lang_map = followups.get(lang, followups["en"])
    result = lang_map.get(intent) or lang_map.get("general") or followups["en"]["general"]
    return result[:3]


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
