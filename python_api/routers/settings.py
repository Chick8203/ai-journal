import json
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from ..database import get_db

router = APIRouter(prefix="/settings", tags=["settings"])


class AISettings(BaseModel):
    ai_provider: str = "gemini"
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    local_base_url: Optional[str] = None
    local_model: Optional[str] = None
    local_embedding_model: Optional[str] = None


def _mask_key(key: str | None) -> str | None:
    if not key or len(key) < 8:
        return key
    return key[:4] + "•" * (len(key) - 8) + key[-4:]


@router.get("/ai")
def get_ai_settings():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT key, value FROM settings WHERE key IN ("
            "'ai_provider', 'gemini_api_key', 'openai_api_key', "
            "'local_base_url', 'local_model', 'local_embedding_model'"
            ")"
        ).fetchall()
        data = {r["key"]: r["value"] for r in rows}
        return {
            "ai_provider": data.get("ai_provider", "gemini"),
            "gemini_api_key_set": bool(data.get("gemini_api_key")),
            "openai_api_key_set": bool(data.get("openai_api_key")),
            "gemini_api_key_preview": _mask_key(data.get("gemini_api_key")),
            "openai_api_key_preview": _mask_key(data.get("openai_api_key")),
            "local_base_url": data.get("local_base_url", "") or "",
            "local_model": data.get("local_model", "") or "",
            "local_embedding_model": data.get("local_embedding_model", "") or "",
        }


def _upsert(conn, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO settings (key, value, updated_at) VALUES (?, ?, datetime('now')) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
        (key, value),
    )


@router.put("/ai")
def update_ai_settings(body: AISettings):
    with get_db() as conn:
        _upsert(conn, "ai_provider", body.ai_provider)
        if body.gemini_api_key is not None:
            if body.gemini_api_key == "":
                conn.execute("DELETE FROM settings WHERE key = 'gemini_api_key'")
            else:
                _upsert(conn, "gemini_api_key", body.gemini_api_key)
        if body.openai_api_key is not None:
            if body.openai_api_key == "":
                conn.execute("DELETE FROM settings WHERE key = 'openai_api_key'")
            else:
                _upsert(conn, "openai_api_key", body.openai_api_key)
        if body.local_base_url is not None:
            _upsert(conn, "local_base_url", body.local_base_url.strip())
        if body.local_model is not None:
            _upsert(conn, "local_model", body.local_model.strip())
        if body.local_embedding_model is not None:
            _upsert(conn, "local_embedding_model", body.local_embedding_model.strip())
    return get_ai_settings()


# ── Template management ────────────────────────────────────────────────────────

_TEMPLATES_KEY = "journal_templates"

_DEFAULT_TEMPLATES = [
    {"id": "freeform",     "name": "自由格式", "content": ""},
    {"id": "engineering",  "name": "工程開發",  "content": "【今日目標】\n\n【完成事項】\n-\n\n【遇到瓶頸】\n\n【明日計畫】"},
    {"id": "office",       "name": "一般辦公",  "content": "【今日重點】\n\n【心得筆記】\n-\n\n【行動項目】"},
]


def _read_templates(conn) -> list:
    row = conn.execute(
        "SELECT value FROM settings WHERE key = ?", (_TEMPLATES_KEY,)
    ).fetchone()
    if row:
        return json.loads(row["value"])
    return list(_DEFAULT_TEMPLATES)


def _write_templates(conn, templates: list) -> None:
    conn.execute(
        "INSERT INTO settings (key, value, updated_at) VALUES (?, ?, datetime('now')) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
        (_TEMPLATES_KEY, json.dumps(templates, ensure_ascii=False)),
    )


class TemplateBody(BaseModel):
    name: str
    content: str


@router.get("/templates")
def get_templates():
    with get_db() as conn:
        return _read_templates(conn)


@router.post("/templates", status_code=201)
def create_template(body: TemplateBody):
    with get_db() as conn:
        templates = _read_templates(conn)
        new = {"id": str(uuid.uuid4()), "name": body.name, "content": body.content}
        templates.append(new)
        _write_templates(conn, templates)
        return new


@router.put("/templates/{template_id}")
def update_template(template_id: str, body: TemplateBody):
    with get_db() as conn:
        templates = _read_templates(conn)
        for t in templates:
            if t["id"] == template_id:
                t["name"] = body.name
                t["content"] = body.content
                _write_templates(conn, templates)
                return t
        raise HTTPException(status_code=404, detail="Template not found")


@router.delete("/templates/{template_id}", status_code=204)
def delete_template(template_id: str):
    with get_db() as conn:
        templates = _read_templates(conn)
        remaining = [t for t in templates if t["id"] != template_id]
        if len(remaining) == len(templates):
            raise HTTPException(status_code=404, detail="Template not found")
        if not remaining:
            raise HTTPException(status_code=400, detail="Cannot delete the last template")
        _write_templates(conn, remaining)


# ── Category management ────────────────────────────────────────────────────────

_CATEGORIES_KEY = "project_categories"

_DEFAULT_CATEGORIES = [
    {"id": "engineering", "name": "工程開發"},
    {"id": "office",      "name": "一般辦公"},
    {"id": "general",     "name": "一般"},
]


def _read_categories(conn) -> list:
    row = conn.execute(
        "SELECT value FROM settings WHERE key = ?", (_CATEGORIES_KEY,)
    ).fetchone()
    if row:
        return json.loads(row["value"])
    return list(_DEFAULT_CATEGORIES)


def _write_categories(conn, categories: list) -> None:
    conn.execute(
        "INSERT INTO settings (key, value, updated_at) VALUES (?, ?, datetime('now')) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
        (_CATEGORIES_KEY, json.dumps(categories, ensure_ascii=False)),
    )


class CategoryBody(BaseModel):
    name: str


@router.get("/categories")
def get_categories():
    with get_db() as conn:
        return _read_categories(conn)


@router.post("/categories", status_code=201)
def create_category(body: CategoryBody):
    with get_db() as conn:
        categories = _read_categories(conn)
        new = {"id": str(uuid.uuid4()), "name": body.name}
        categories.append(new)
        _write_categories(conn, categories)
        return new


@router.delete("/categories/{category_id}", status_code=204)
def delete_category(category_id: str):
    with get_db() as conn:
        categories = _read_categories(conn)
        remaining = [c for c in categories if c["id"] != category_id]
        if len(remaining) == len(categories):
            raise HTTPException(status_code=404, detail="Category not found")
        if not remaining:
            raise HTTPException(status_code=400, detail="Cannot delete the last category")
        _write_categories(conn, remaining)
