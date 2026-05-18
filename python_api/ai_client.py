"""
Unified AI client supporting Google Gemini and OpenAI.
Provider and API keys are stored in the settings table.
"""
import requests
from .database import get_db


def get_ai_settings() -> dict:
    try:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT key, value FROM settings WHERE key IN ("
                "'ai_provider', 'gemini_api_key', 'openai_api_key', "
                "'local_base_url', 'local_model', 'local_embedding_model'"
                ")"
            ).fetchall()
            return {r["key"]: r["value"] for r in rows}
    except Exception:
        return {}


# ────────────────────────────────────────────────────────────────────────────────
# Embeddings (RAG semantic search)
# ────────────────────────────────────────────────────────────────────────────────

def get_active_embedding_info() -> tuple[str, str]:
    """Return (provider, model_id) for the currently active embedding setup."""
    settings = get_ai_settings()
    provider = settings.get("ai_provider", "gemini")
    if provider == "openai":
        return ("openai", "text-embedding-3-small")
    if provider == "local":
        return ("local", settings.get("local_embedding_model") or "nomic-embed-text")
    return ("gemini", "text-embedding-004")


def generate_embedding(text: str) -> tuple[list[float], str, str]:
    """Generate an embedding for the given text using the active provider.

    Returns (vector, provider, model_id). Raises RuntimeError on failure.
    """
    settings = get_ai_settings()
    provider = settings.get("ai_provider", "gemini")
    text = (text or "").strip()
    if not text:
        raise RuntimeError("Cannot embed empty text")

    if provider == "openai":
        key = settings.get("openai_api_key", "")
        if not key:
            raise RuntimeError("尚未設定 OpenAI API 金鑰")
        return (_embed_openai(text, key), "openai", "text-embedding-3-small")

    if provider == "local":
        base = settings.get("local_base_url") or "http://localhost:11434/v1"
        model = settings.get("local_embedding_model") or "nomic-embed-text"
        return (_embed_local(text, base, model), "local", model)

    key = settings.get("gemini_api_key", "")
    if not key:
        raise RuntimeError("尚未設定 Gemini API 金鑰")
    return (_embed_gemini(text, key), "gemini", "text-embedding-004")


def _embed_gemini(text: str, api_key: str) -> list[float]:
    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        f"models/text-embedding-004:embedContent?key={api_key}"
    )
    payload = {"content": {"parts": [{"text": text}]}}
    resp = requests.post(url, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()["embedding"]["values"]


def _embed_openai(text: str, api_key: str) -> list[float]:
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    resp = client.embeddings.create(model="text-embedding-3-small", input=text)
    return resp.data[0].embedding


def _embed_local(text: str, base_url: str, model: str) -> list[float]:
    from openai import OpenAI

    try:
        client = OpenAI(api_key="local", base_url=base_url.rstrip("/"))
        resp = client.embeddings.create(model=model, input=text)
        return resp.data[0].embedding
    except Exception as e:
        msg = str(e)
        if "Connection" in msg or "refused" in msg.lower():
            raise RuntimeError(
                f"無法連線到本地模型 ({base_url})，請確認 Ollama / LM Studio 已啟動"
            )
        if "not found" in msg.lower() or "404" in msg:
            raise RuntimeError(
                f"找不到 embedding 模型「{model}」。Ollama 需先執行 `ollama pull {model}`"
            )
        raise RuntimeError(f"本地 embedding 呼叫失敗：{msg}")


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two equal-length vectors, pure Python."""
    if not a or not b or len(a) != len(b):
        return 0.0
    import math

    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def generate_text(prompt: str, system: str | None = None, json_mode: bool = False) -> str:
    settings = get_ai_settings()
    provider = settings.get("ai_provider", "gemini")
    gemini_key = settings.get("gemini_api_key", "")
    openai_key = settings.get("openai_api_key", "")
    local_base_url = settings.get("local_base_url", "") or "http://localhost:11434/v1"
    local_model = settings.get("local_model", "") or "llama3.2"

    full_prompt = prompt
    if system:
        full_prompt = f"[System Instructions]\n{system}\n\n[User Request]\n{prompt}"

    if provider == "openai":
        if not openai_key:
            raise RuntimeError("尚未設定 OpenAI API 金鑰，請至設定頁面填入金鑰。")
        return _call_openai(full_prompt, openai_key, json_mode=json_mode)
    elif provider == "local":
        return _call_local(full_prompt, local_base_url, local_model, json_mode=json_mode)
    else:
        if not gemini_key:
            raise RuntimeError("尚未設定 Gemini API 金鑰，請至設定頁面填入金鑰。")
        return _call_gemini(full_prompt, gemini_key)


def _call_gemini(prompt: str, api_key: str) -> str:
    # Try models in order of preference across both API versions
    attempts = [
        ("v1beta", "gemini-2.5-flash"),
        ("v1beta", "gemini-2.5-flash-preview-05-20"),
        ("v1beta", "gemini-2.0-flash"),
        ("v1beta", "gemini-2.0-flash-lite"),
        ("v1", "gemini-1.5-flash"),
        ("v1beta", "gemini-1.5-flash"),
        ("v1", "gemini-pro"),
    ]

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 8192},
    }

    last_error = "未知錯誤"
    for version, model in attempts:
        url = (
            f"https://generativelanguage.googleapis.com"
            f"/{version}/models/{model}:generateContent?key={api_key}"
        )
        try:
            resp = requests.post(url, json=payload, timeout=60)
            if resp.status_code == 404:
                last_error = f"模型 {model} 不存在"
                continue
            resp.raise_for_status()
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except requests.HTTPError as e:
            last_error = f"{model}: {e}"
            continue
        except Exception as e:
            last_error = str(e)
            continue

    raise RuntimeError(f"Gemini API 呼叫失敗：{last_error}")


def _call_openai(prompt: str, api_key: str, json_mode: bool = False) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    kwargs: dict = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 8192,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.content or ""


def _call_local(prompt: str, base_url: str, model: str, json_mode: bool = False) -> str:
    from openai import OpenAI

    base = base_url.rstrip("/")
    try:
        client = OpenAI(api_key="local", base_url=base)
        kwargs: dict = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 8192,
            "timeout": 300,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""
    except Exception as e:
        msg = str(e)
        if "Connection" in msg or "refused" in msg.lower():
            raise RuntimeError(
                f"無法連線到本地模型 ({base})，請確認 Ollama 或 LM Studio 已啟動。"
            )
        if "model" in msg.lower() and ("not found" in msg.lower() or "404" in msg):
            raise RuntimeError(
                f"找不到模型「{model}」，請確認模型名稱正確（Ollama 可用 `ollama list` 查看）。"
            )
        raise RuntimeError(f"本地模型呼叫失敗：{msg}")
