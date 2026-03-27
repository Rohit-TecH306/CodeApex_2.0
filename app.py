import os
from dotenv import load_dotenv

load_dotenv()

from io import BytesIO

from flask import Flask, jsonify, render_template, request, send_file, session
from gtts import gTTS

from embeddings.search import USER_BY_MOBILE, answer_query, detect_language, get_refiner_status

app = Flask(__name__, template_folder="web/templates", static_folder="web/static")
app.config["SECRET_KEY"] = os.getenv("BANK_ASSISTANT_SECRET", "dev-secret-change-me")


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

    resolved_lang = detect_language(message) if requested_lang == "auto" else requested_lang
    if resolved_lang not in {"en", "hi", "mr"}:
        resolved_lang = "en"

    answer = answer_query(user, message, lang_hint=resolved_lang)

    return jsonify({"answer": answer, "language": resolved_lang}), 200


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
