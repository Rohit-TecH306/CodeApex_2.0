import os
from dotenv import load_dotenv

load_dotenv()

from io import BytesIO

from flask import Flask, jsonify, render_template, request, send_file, session
from gtts import gTTS

from embeddings.search import (
    USER_BY_MOBILE,
    CREDIT_PROFILE_BY_USER,
    TXNS_BY_USER,
    answer_query,
    detect_language,
    get_follow_up_suggestions,
    get_refiner_status,
)

app = Flask(__name__, template_folder="web/templates", static_folder="web/static")
app.config["SECRET_KEY"] = os.getenv("BANK_ASSISTANT_SECRET", "dev-secret-change-me")


def _contains_devanagari(text: str) -> bool:
    return any("\u0900" <= ch <= "\u097f" for ch in text)


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/api/health")
def health() -> tuple:
    return jsonify({"status": "ok"}), 200


@app.get("/api/model-status")
def model_status() -> tuple:
    return jsonify(get_refiner_status()), 200


@app.post("/api/login")
def login() -> tuple:
    payload = request.get_json(silent=True) or {}
    mobile = str(payload.get("mobile", "")).strip()

    user = USER_BY_MOBILE.get(mobile)
    if not user:
        return jsonify({"error": "Invalid mobile number"}), 401

    session["mobile"] = mobile
    return (
        jsonify(
            {
                "ok": True,
                "user": {
                    "name": user.get("name", "User"),
                    "district": user.get("district", ""),
                    "user_type": user.get("user_type", ""),
                    "mobile": mobile,
                },
            }
        ),
        200,
    )


@app.post("/api/logout")
def logout() -> tuple:
    session.clear()
    return jsonify({"ok": True}), 200


@app.get("/api/user-data")
def user_data() -> tuple:
    mobile = session.get("mobile")
    if not mobile:
        return jsonify({"error": "Not logged in"}), 401

    user = USER_BY_MOBILE.get(mobile)
    if not user:
        return jsonify({"error": "Session expired"}), 401
    
    user_id = user.get("user_id")
    profile = CREDIT_PROFILE_BY_USER.get(user_id, {})
    txns = TXNS_BY_USER.get(user_id, [])
    
    return jsonify({
        "credit_profile": profile,
        "transactions": txns
    }), 200


@app.post("/api/chat")
def chat() -> tuple:
    mobile = session.get("mobile")
    if not mobile:
        return jsonify({"error": "Not logged in"}), 401

    user = USER_BY_MOBILE.get(mobile)
    if not user:
        session.clear()
        return jsonify({"error": "Session expired"}), 401

    payload = request.get_json(silent=True) or {}
    message = str(payload.get("message", "")).strip()
    requested_lang = str(payload.get("language", "auto")).strip().lower()

    if not message:
        return jsonify({"error": "Message is required"}), 400

    # If query clearly contains Devanagari, prefer automatic language detection
    # even when frontend accidentally sends English as the requested language.
    if requested_lang == "auto" or (requested_lang == "en" and _contains_devanagari(message)):
        resolved_lang = detect_language(message)
    else:
        resolved_lang = requested_lang

    if resolved_lang not in {"en", "hi", "mr"}:
        resolved_lang = "en"

    answer = answer_query(user, message, lang_hint=resolved_lang)
    follow_ups = get_follow_up_suggestions(message, lang_hint=resolved_lang)

    return jsonify({"answer": answer, "language": resolved_lang, "follow_ups": follow_ups}), 200


@app.post("/api/calculate-emi")
def calculate_emi_endpoint() -> tuple:
    mobile = session.get("mobile")
    if not mobile:
        return jsonify({"error": "Not logged in"}), 401

    user = USER_BY_MOBILE.get(mobile)
    if not user:
        return jsonify({"error": "Session expired"}), 401
        
    user_id = user["user_id"]
    profile = CREDIT_PROFILE_BY_USER.get(user_id)
    
    if not profile:
        return jsonify({"error": "No credit profile found for this user."}), 404

    payload = request.get_json(silent=True) or {}
    principal = float(payload.get("principal", 0))
    duration_years = float(payload.get("duration", 0))
    
    if principal <= 0 or duration_years <= 0:
        return jsonify({"error": "Invalid principal or duration"}), 400

    # Determine Interest Rate based on CIBIL score
    cibil = profile.get("cibil_score", 0)
    if cibil >= 800:
        annual_rate = 8.5
    elif cibil >= 700:
        annual_rate = 10.0
    elif cibil >= 600:
        annual_rate = 12.0
    else:
        annual_rate = 15.0

    r = (annual_rate / 12) / 100
    n = duration_years * 12
    try:
        emi = principal * r * ((1 + r)**n) / (((1 + r)**n) - 1)
        emi = round(emi, 2)
    except ZeroDivisionError:
        emi = 0

    return jsonify({
        "principal": principal,
        "duration_years": duration_years,
        "interest_rate": annual_rate,
        "cibil_score": cibil,
        "emi": emi,
        "credit_rating": profile.get("credit_rating", "N/A"),
        "loan_approval_likelihood": profile.get("loan_approval_likelihood", "N/A")
    }), 200


@app.post("/api/tts")
def tts() -> tuple:
    mobile = session.get("mobile")
    if not mobile or mobile not in USER_BY_MOBILE:
        return jsonify({"error": "Not logged in"}), 401

    payload = request.get_json(silent=True) or {}
    text = str(payload.get("text", "")).strip()
    lang = str(payload.get("language", "en")).strip().lower()
    voice_mode = str(payload.get("voice_mode", "stable")).strip().lower()

    if not text:
        return jsonify({"error": "Text is required"}), 400

    if lang == "auto" or (lang == "en" and _contains_devanagari(text)):
        lang = detect_language(text)

    if lang not in {"en", "hi", "mr"}:
        lang = "en"

    gtts_lang = "mr" if lang == "mr" else ("hi" if lang == "hi" else "en")
    tld = "co.in"
    if voice_mode == "dynamic":
        turn = int(session.get("tts_turn", 0))
        session["tts_turn"] = turn + 1
        tld_options = {
            "en": ["co.in", "co.uk", "com.au", "us"],
            "hi": ["co.in", "co.uk"],
            "mr": ["co.in", "co.uk"],
        }
        candidates = tld_options.get(gtts_lang, ["co.in"])
        tld = candidates[turn % len(candidates)]

    try:
        tts_engine = gTTS(text=text, lang=gtts_lang, tld=tld, slow=False)
        audio = BytesIO()
        tts_engine.write_to_fp(audio)
        audio.seek(0)
    except Exception:
        try:
            tts_engine = gTTS(text=text, lang=gtts_lang, tld="co.in", slow=False)
            audio = BytesIO()
            tts_engine.write_to_fp(audio)
            audio.seek(0)
        except Exception:
            return jsonify({"error": "TTS generation failed"}), 500

    return send_file(audio, mimetype="audio/mpeg", as_attachment=False, download_name="reply.mp3")


@app.post("/api/tts-stop")
def tts_stop() -> tuple:
    """Clear TTS state for immediate playback stop on frontend."""
    session["tts_stop_requested"] = True
    return jsonify({"ok": True}), 200


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
