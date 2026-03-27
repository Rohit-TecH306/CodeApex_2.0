import importlib
import os
import tempfile

from search import USER_BY_MOBILE, answer_query, detect_language


def safe_input(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except EOFError:
        return ""


def pick_voice_id(engine, lang: str):
    voices = engine.getProperty("voices") or []
    if not voices:
        return None

    # Windows SAPI voices often expose locale/name fields differently.
    preferred_tokens = {
        "en": ["en", "english", "india"],
        "hi": ["hi", "hindi", "india"],
        "mr": ["mr", "marathi", "india"],
    }.get(lang, ["en", "english"])

    for v in voices:
        haystack = " ".join(
            [
                str(getattr(v, "id", "")),
                str(getattr(v, "name", "")),
                str(getattr(v, "languages", "")),
            ]
        ).lower()
        if all(token in haystack for token in preferred_tokens[:2]):
            return v.id

    # Relaxed fallback search for at least one token match.
    for v in voices:
        haystack = " ".join(
            [
                str(getattr(v, "id", "")),
                str(getattr(v, "name", "")),
                str(getattr(v, "languages", "")),
            ]
        ).lower()
        if any(token in haystack for token in preferred_tokens):
            return v.id

    return None


def create_tts_engine(pyttsx3_module, lang: str):
    engine = pyttsx3_module.init()
    engine.setProperty("volume", 1.0)
    voice_id = pick_voice_id(engine, lang)
    if voice_id:
        engine.setProperty("voice", voice_id)
    return engine


def speak(pyttsx3_module, text: str, lang: str) -> None:
    # Use a fresh engine each turn to avoid stale pyttsx3 state on Windows.
    cleaned = " ".join(text.splitlines()).strip()
    if not cleaned:
        return

    # First attempt
    try:
        engine = create_tts_engine(pyttsx3_module, lang)
        engine.say(cleaned)
        engine.runAndWait()
        engine.stop()
        return
    except Exception:
        pass

    # Retry once with English fallback voice/rate for maximum compatibility.
    try:
        engine = create_tts_engine(pyttsx3_module, "en")
        engine.setProperty("rate", 170)
        engine.say(cleaned)
        engine.runAndWait()
        engine.stop()
    except Exception:
        print("TTS warning: could not play audio for this response.")


def speak_with_gtts(gtts_module, playsound_func, text: str, lang: str) -> bool:
    cleaned = " ".join(text.splitlines()).strip()
    if not cleaned:
        return True

    tmp_path = None
    try:
        tts = gtts_module.gTTS(text=cleaned, lang=lang)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
            tmp_path = f.name
        tts.save(tmp_path)
        playsound_func(tmp_path)
        return True
    except Exception:
        return False
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def _normalize_for_score(text: str) -> str:
    return " ".join(text.lower().split())


def choose_best_candidate(candidates: dict) -> tuple[str, str]:
    if not candidates:
        raise RuntimeError("No speech candidates available")

    bank_markers = [
        "balance", "account", "transaction", "statement", "loan", "kyc", "upi", "pin",
        "बैलेंस", "खाता", "लेनदेन", "कर्ज", "केवाईसी", "शिल्लक", "खाते", "व्यवहार",
        "khata", "len den", "vyavhar", "karj", "byaaj",
    ]
    locale_to_lang = {"en-IN": "en", "hi-IN": "hi", "mr-IN": "mr"}

    best_locale = None
    best_text = None
    best_score = float("-inf")

    for locale, raw_text in candidates.items():
        text = raw_text.strip()
        if not text:
            continue

        expected_lang = locale_to_lang.get(locale, "en")
        detected_lang = detect_language(text)
        norm = _normalize_for_score(text)
        has_devanagari = any("\u0900" <= ch <= "\u097f" for ch in text)

        score = 0.0
        if detected_lang == expected_lang:
            score += 4.0
        if has_devanagari and expected_lang in {"hi", "mr"}:
            score += 2.0
        if (not has_devanagari) and expected_lang == "en":
            score += 1.0

        score += sum(1 for marker in bank_markers if marker in norm)
        score += min(len(text.split()), 8) * 0.05

        if score > best_score:
            best_score = score
            best_locale = locale
            best_text = text

    if not best_text:
        raise RuntimeError("Unable to choose speech candidate")

    return best_text, best_locale


def recognize_multilang(recognizer, audio) -> tuple[str, str]:
    # Collect recognition candidates for all supported locales and choose best fit.
    candidates = {}
    for locale in ("en-IN", "hi-IN", "mr-IN"):
        try:
            text = recognizer.recognize_google(audio, language=locale)
            if text and text.strip():
                candidates[locale] = text.strip()
        except Exception:
            continue

    return choose_best_candidate(candidates)


def configure_voice(engine, lang: str) -> None:
    # Keep this simple and reliable across Windows voice installations.
    if lang == "hi":
        engine.setProperty("rate", 165)
    elif lang == "mr":
        engine.setProperty("rate", 165)
    else:
        engine.setProperty("rate", 175)


def choose_asr_language(lang: str) -> str:
    mapping = {
        "en": "en-IN",
        "hi": "hi-IN",
        "mr": "mr-IN",
    }
    return mapping.get(lang, "en-IN")


def main() -> None:
    try:
        sr = importlib.import_module("speech_recognition")
        pyttsx3 = importlib.import_module("pyttsx3")
    except ModuleNotFoundError:
        print("Missing voice dependencies.")
        print("Install with: pip install SpeechRecognition pyttsx3 PyAudio")
        return

    # Optional multilingual TTS backend for Hindi/Marathi.
    gtts = None
    playsound_func = None
    try:
        gtts = importlib.import_module("gtts")
        playsound_module = importlib.import_module("playsound")
        playsound_func = playsound_module.playsound
    except ModuleNotFoundError:
        print("Tip: For better Hindi/Marathi voice, install: pip install gTTS playsound==1.2.2")

    recognizer = sr.Recognizer()

    print("Voice Banking Assistant started.")
    print("Supported voice languages: English/Hindi/Marathi")
    print("Mode options:")
    print("1) voice  -> listen from microphone")
    print("2) text   -> type questions manually")
    print("Type 'exit' to quit from any mode.")

    mode = safe_input("Select mode (voice/text) [voice]: ")
    if not mode:
        mode = "voice"
    mode = mode.lower()
    if mode not in {"voice", "text", "1", "2"}:
        print("Invalid mode. Using voice mode.")
        mode = "voice"
    if mode == "1":
        mode = "voice"
    if mode == "2":
        mode = "text"

    mobile = safe_input("Enter mobile number to login: ")
    if not mobile:
        print("No mobile input received. Exiting.")
        return
    user = USER_BY_MOBILE.get(mobile)
    if not user:
        print("User not found.")
        print("Try one of these demo numbers:")
        for m in list(USER_BY_MOBILE.keys())[:5]:
            print(f"- {m}")
        return

    print("Login successful.")
    if mode == "voice":
        print("Speak after the pause.")
    else:
        print("Type your question.")
    print("Say/type 'exit' to quit.")

    while True:
        if mode == "text":
            text = safe_input("Text input: ")
            if not text:
                print("No input received. Please type a question or 'exit'.")
                continue
        else:
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                print("Listening...")
                audio = recognizer.listen(source, phrase_time_limit=8)

            try:
                text, asr_locale = recognize_multilang(recognizer, audio)
                print(f"Detected via {asr_locale}")
            except Exception:
                print("Could not understand voice. Please type your question:")
                text = safe_input("Text fallback: ")
                if not text:
                    print("No fallback input. Continuing in voice mode.")
                    continue

        if not text:
            continue

        if text.lower() == "exit":
            bye = "Goodbye!"
            print(bye)
            speak(pyttsx3, bye, "en")
            break

        lang = detect_language(text)

        # Retry STT in language-specific mode if user typed Devanagari via fallback.
        if any("\u0900" <= ch <= "\u097f" for ch in text):
            asr_lang = choose_asr_language(lang)
            _ = asr_lang  # placeholder for future language-forced recognition mode

        answer = answer_query(user, text)
        print(f"You said: {text}")
        print(f"Assistant: {answer}")

        # Prefer cloud TTS for Hindi/Marathi when available; fallback to local TTS.
        if lang in {"hi", "mr"} and gtts and playsound_func:
            ok = speak_with_gtts(gtts, playsound_func, answer, lang)
            if not ok:
                speak(pyttsx3, answer, lang)
        else:
            speak(pyttsx3, answer, lang)


if __name__ == "__main__":
    main()
