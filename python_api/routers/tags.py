from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import Optional
from ..database import get_db

router = APIRouter(prefix="/tags", tags=["tags"])

TAG_COLORS = [
    "#ef4444", "#f97316", "#eab308", "#22c55e", "#06b6d4",
    "#3b82f6", "#8b5cf6", "#ec4899", "#14b8a6", "#f59e0b",
    "#10b981", "#6366f1",
]


class CreateTagBody(BaseModel):
    name: str
    color: Optional[str] = None


def _next_color(conn) -> str:
    count = conn.execute("SELECT COUNT(*) as c FROM tags").fetchone()["c"]
    return TAG_COLORS[count % len(TAG_COLORS)]


@router.get("")
def list_tags(search: Optional[str] = Query(None)):
    with get_db() as conn:
        if search:
            rows = conn.execute(
                "SELECT id, name, color FROM tags WHERE name LIKE ? ORDER BY name ASC LIMIT 30",
                (f"%{search}%",),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, name, color FROM tags ORDER BY name ASC"
            ).fetchall()
        return [{"id": r["id"], "name": r["name"], "color": r["color"]} for r in rows]


@router.delete("/{tag_id}", status_code=204)
def delete_tag(tag_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT id FROM tags WHERE id = ?", (tag_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Tag not found")
        conn.execute("DELETE FROM tags WHERE id = ?", (tag_id,))


@router.post("", status_code=201)
def create_tag(body: CreateTagBody):
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Tag name cannot be empty")
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id, name, color FROM tags WHERE name = ?", (name,)
        ).fetchone()
        if existing:
            return {"id": existing["id"], "name": existing["name"], "color": existing["color"]}
        color = body.color or _next_color(conn)
        cur = conn.execute(
            "INSERT INTO tags (name, color) VALUES (?, ?)", (name, color)
        )
        return {"id": cur.lastrowid, "name": name, "color": color}
