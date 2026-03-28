const API_BASE = "/api";

export async function loginByMobile(mobile) {
  const res = await fetch(`${API_BASE}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ mobile }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "Login failed");
  return data;
}

export async function logoutUser() {
  const res = await fetch(`${API_BASE}/logout`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({}),
  });
  if (!res.ok) throw new Error("Logout failed");
}

export async function processText(query, language = "auto") {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ message: query, language }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "Chat failed");

  return {
    response_text: data.answer,
    language: data.language,
    follow_ups: data.follow_ups || [],
  };
}

export async function getTtsAudio(text, language = "en", voiceMode = "stable") {
  const res = await fetch(`${API_BASE}/tts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ text, language, voice_mode: voiceMode }),
  });
  if (!res.ok) throw new Error("TTS failed");
  return res.blob();
}

export async function stopTts() {
  const res = await fetch(`${API_BASE}/tts-stop`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({}),
  });
  if (!res.ok) throw new Error("Stop TTS failed");
}

export async function calculateEmi(principal, duration) {
  const res = await fetch(`${API_BASE}/calculate-emi`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ principal, duration }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "EMI calculation failed");
  return data;
}

export async function getUserData() {
  const res = await fetch(`${API_BASE}/user-data`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "Failed to fetch user data");
  return data;
}
