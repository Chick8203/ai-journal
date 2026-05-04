"""
Unified AI client that supports Gemini and OpenAI (ChatGPT).
Priority:
  1. User-configured provider + key from settings table
  2. Replit Gemini AI Integration (fallback, no key needed)
"""
import os
import requests
from .database import get_db


def get_ai_settings() -> dict:
    try:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT key, value FROM settings WHERE key IN ('ai_provider', 'gemini_api_key', 'openai_api_key')"
            ).fetchall()
            return {r["key"]: r["value"] for r in rows}
    except Exception:
        return {}


def generate_text(prompt: str, system: str | None = None) -> str:
    settings = get_ai_settings()
    provider = settings.get("ai_provider", "replit")
    gemini_key = settings.get("gemini_api_key", "")
    openai_key = settings.get("openai_api_key", "")

    full_prompt = prompt
    if system:
        full_prompt = f"[System Instructions]\n{system}\n\n[User Request]\n{prompt}"

    if provider == "openai" and openai_key:
        return _call_openai(full_prompt, openai_key)
    elif provider == "gemini" and gemini_key:
        return _call_gemini_with_key(full_prompt, gemini_key)
    else:
        return _call_replit_gemini(full_prompt)


def _call_replit_gemini(prompt: str) -> str:
    """Call Gemini via Replit AI Integration proxy using direct HTTP requests."""
    api_key = os.environ.get("AI_INTEGRATIONS_GEMINI_API_KEY", "dummy")
    base_url = os.environ.get("AI_INTEGRATIONS_GEMINI_BASE_URL", "").rstrip("/")

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 8192},
    }

    models = ["gemini-2.5-flash", "gemini-2.5-pro"]
    last_exc: Exception = RuntimeError("No models available")

    for model in models:
        url = f"{base_url}/models/{model}:generateContent?key={api_key}"
        try:
            resp = requests.post(url, json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return text
        except Exception as e:
            last_exc = e
            continue

    raise last_exc


def _call_gemini_with_key(prompt: str, api_key: str) -> str:
    from google import genai
    from google.genai import types as genai_types

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[genai_types.Content(role="user", parts=[genai_types.Part(text=prompt)])],
        config=genai_types.GenerateContentConfig(max_output_tokens=8192),
    )
    return response.text or ""


def _call_openai(prompt: str, api_key: str) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=8192,
    )
    return response.choices[0].message.content or ""
