from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from ..database import get_db

router = APIRouter(prefix="/settings", tags=["settings"])


class AISettings(BaseModel):
    ai_provider: str = "replit"
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None


def _mask_key(key: str | None) -> str | None:
    if not key or len(key) < 8:
        return key
    return key[:4] + "•" * (len(key) - 8) + key[-4:]


@router.get("/ai")
def get_ai_settings():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT key, value FROM settings WHERE key IN ('ai_provider', 'gemini_api_key', 'openai_api_key')"
        ).fetchall()
        data = {r["key"]: r["value"] for r in rows}
        return {
            "ai_provider": data.get("ai_provider", "replit"),
            "gemini_api_key_set": bool(data.get("gemini_api_key")),
            "openai_api_key_set": bool(data.get("openai_api_key")),
            "gemini_api_key_preview": _mask_key(data.get("gemini_api_key")),
            "openai_api_key_preview": _mask_key(data.get("openai_api_key")),
        }


@router.put("/ai")
def update_ai_settings(body: AISettings):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO settings (key, value, updated_at) VALUES ('ai_provider', ?, datetime('now')) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (body.ai_provider,),
        )
        if body.gemini_api_key is not None:
            if body.gemini_api_key == "":
                conn.execute("DELETE FROM settings WHERE key = 'gemini_api_key'")
            else:
                conn.execute(
                    "INSERT INTO settings (key, value, updated_at) VALUES ('gemini_api_key', ?, datetime('now')) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                    (body.gemini_api_key,),
                )
        if body.openai_api_key is not None:
            if body.openai_api_key == "":
                conn.execute("DELETE FROM settings WHERE key = 'openai_api_key'")
            else:
                conn.execute(
                    "INSERT INTO settings (key, value, updated_at) VALUES ('openai_api_key', ?, datetime('now')) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                    (body.openai_api_key,),
                )
    return get_ai_settings()
