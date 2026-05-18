import json
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from ..database import get_db
from ..ai_client import generate_embedding

router = APIRouter(prefix="/entries", tags=["entries"])

TAG_COLORS = [
    "#ef4444", "#f97316", "#eab308", "#22c55e", "#06b6d4",
    "#3b82f6", "#8b5cf6", "#ec4899", "#14b8a6", "#f59e0b",
    "#10b981", "#6366f1",
]

_ENTRY_SELECT = """
    SELECT e.*, p.name as project_name,
        GROUP_CONCAT(
            CAST(t.id AS TEXT) || ';;;' || t.name || ';;;' || t.color,
            '|||'
        ) as tag_data
    FROM entries e
    JOIN projects p ON p.id = e.project_id
    LEFT JOIN log_tags lt ON lt.log_id = e.id
    LEFT JOIN tags t ON t.id = lt.tag_id
"""

_ENTRY_GROUP = "GROUP BY e.id"


class EntryCreate(BaseModel):
    date: str
    title: Optional[str] = None
    content: str
    projectId: int
    template: str = "freeform"
    mood: Optional[int] = None
    tags: list[str] = []


class EntryUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    mood: Optional[int] = None
    tags: Optional[list[str]] = None


def _parse_tag_data(tag_data: str | None) -> list[dict]:
    if not tag_data:
        return []
    tags = []
    for record in tag_data.split("|||"):
        parts = record.split(";;;")
        if len(parts) == 3 and parts[0].isdigit():
            tags.append({"id": int(parts[0]), "name": parts[1], "color": parts[2]})
    return tags


def row_to_entry(row) -> dict:
    keys = row.keys()
    if "tag_data" in keys:
        tags = _parse_tag_data(row["tag_data"])
    else:
        tags = []
        try:
            for name in json.loads(row["tags"] or "[]"):
                tags.append({"id": 0, "name": name, "color": "#6366f1"})
        except Exception:
            pass

    return {
        "id": row["id"],
        "date": row["date"],
        "title": row["title"] if "title" in keys else None,
        "content": row["content"],
        "projectId": row["project_id"],
        "projectName": row["project_name"] if "project_name" in keys else "",
        "template": row["template"],
        "mood": row["mood"],
        "tags": tags,
        "createdAt": row["created_at"],
    }


def _try_embed_entry(conn, entry_id: int, content: str) -> None:
    """Best-effort: generate and store embedding for an entry. Silent on failure."""
    try:
        vec, provider, model = generate_embedding(content)
        conn.execute(
            "UPDATE entries SET embedding = ?, embedding_provider = ?, embedding_model = ? WHERE id = ?",
            (json.dumps(vec), provider, model, entry_id),
        )
    except Exception:
        # Embedding service down or no key — entry still saves, can backfill later.
        pass


def _sync_tags(conn, entry_id: int, tag_names: list[str]):
    conn.execute("DELETE FROM log_tags WHERE log_id = ?", (entry_id,))
    resolved_names = []
    for raw in tag_names:
        name = raw.strip()
        if not name:
            continue
        resolved_names.append(name)
        existing = conn.execute(
            "SELECT id FROM tags WHERE name = ?", (name,)
        ).fetchone()
        if existing:
            tag_id = existing["id"]
        else:
            count = conn.execute("SELECT COUNT(*) as c FROM tags").fetchone()["c"]
            color = TAG_COLORS[count % len(TAG_COLORS)]
            cur = conn.execute(
                "INSERT INTO tags (name, color) VALUES (?, ?)", (name, color)
            )
            tag_id = cur.lastrowid
        conn.execute(
            "INSERT OR IGNORE INTO log_tags (log_id, tag_id) VALUES (?, ?)",
            (entry_id, tag_id),
        )
    conn.execute(
        "UPDATE entries SET tags = ? WHERE id = ?",
        (json.dumps(resolved_names, ensure_ascii=False), entry_id),
    )


@router.get("")
def list_entries(
    projectId: Optional[int] = Query(None),
    limit: int = Query(50),
    offset: int = Query(0),
):
    with get_db() as conn:
        if projectId:
            rows = conn.execute(
                f"{_ENTRY_SELECT} WHERE e.project_id = ? {_ENTRY_GROUP} "
                f"ORDER BY e.date DESC, e.created_at DESC LIMIT ? OFFSET ?",
                (projectId, limit, offset),
            ).fetchall()
        else:
            rows = conn.execute(
                f"{_ENTRY_SELECT} {_ENTRY_GROUP} "
                f"ORDER BY e.date DESC, e.created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        return [row_to_entry(r) for r in rows]


@router.post("", status_code=201)
def create_entry(body: EntryCreate):
    with get_db() as conn:
        proj = conn.execute(
            "SELECT id FROM projects WHERE id = ?", (body.projectId,)
        ).fetchone()
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")

        cur = conn.execute(
            "INSERT INTO entries (date, title, content, project_id, template, mood, tags) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                body.date,
                (body.title or "").strip() or None,
                body.content,
                body.projectId,
                body.template,
                body.mood,
                json.dumps([], ensure_ascii=False),
            ),
        )
        entry_id = cur.lastrowid
        _sync_tags(conn, entry_id, body.tags)
        _try_embed_entry(conn, entry_id, body.content)

        row = conn.execute(
            f"{_ENTRY_SELECT} WHERE e.id = ? {_ENTRY_GROUP}",
            (entry_id,),
        ).fetchone()
        return row_to_entry(row)


@router.get("/stats/summary")
def get_entries_summary(projectId: Optional[int] = Query(None)):
    with get_db() as conn:
        if projectId:
            total = conn.execute(
                "SELECT COUNT(*) as c FROM entries WHERE project_id = ?", (projectId,)
            ).fetchone()["c"]
        else:
            total = conn.execute("SELECT COUNT(*) as c FROM entries").fetchone()["c"]

        total_projects = conn.execute(
            "SELECT COUNT(*) as c FROM projects"
        ).fetchone()["c"]

        if projectId:
            recent_rows = conn.execute(
                f"{_ENTRY_SELECT} WHERE e.project_id = ? {_ENTRY_GROUP} "
                f"ORDER BY e.date DESC LIMIT 5",
                (projectId,),
            ).fetchall()
        else:
            recent_rows = conn.execute(
                f"{_ENTRY_SELECT} {_ENTRY_GROUP} ORDER BY e.date DESC LIMIT 5"
            ).fetchall()

        by_project = conn.execute(
            """
            SELECT p.id as project_id, p.name as project_name, COUNT(e.id) as count
            FROM projects p
            LEFT JOIN entries e ON e.project_id = p.id
            WHERE p.status = 'active'
            GROUP BY p.id
            ORDER BY count DESC
            """
        ).fetchall()

        dates = conn.execute(
            "SELECT DISTINCT date FROM entries ORDER BY date DESC LIMIT 365"
        ).fetchall()
        streak = 0
        if dates:
            from datetime import date, timedelta
            today = date.today()
            for i, d in enumerate(dates):
                expected = today - timedelta(days=i)
                if d["date"] == expected.isoformat():
                    streak += 1
                else:
                    break

        return {
            "totalEntries": total,
            "totalProjects": total_projects,
            "recentEntries": [row_to_entry(r) for r in recent_rows],
            "entriesByProject": [
                {
                    "projectId": r["project_id"],
                    "projectName": r["project_name"],
                    "count": r["count"],
                }
                for r in by_project
            ],
            "streak": streak,
        }


@router.get("/{entry_id}")
def get_entry(entry_id: int):
    with get_db() as conn:
        row = conn.execute(
            f"{_ENTRY_SELECT} WHERE e.id = ? {_ENTRY_GROUP}",
            (entry_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Entry not found")
        return row_to_entry(row)


@router.put("/{entry_id}")
def update_entry(entry_id: int, body: EntryUpdate):
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM entries WHERE id = ?", (entry_id,)
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Entry not found")

        updates = []
        params = []
        if body.title is not None:
            updates.append("title = ?")
            params.append(body.title.strip() or None)
        if body.content is not None:
            updates.append("content = ?")
            params.append(body.content)
        if body.mood is not None:
            updates.append("mood = ?")
            params.append(body.mood)

        if updates:
            params.append(entry_id)
            conn.execute(
                f"UPDATE entries SET {', '.join(updates)} WHERE id = ?", params
            )

        if body.tags is not None:
            _sync_tags(conn, entry_id, body.tags)

        # Re-embed if content changed
        if body.content is not None:
            _try_embed_entry(conn, entry_id, body.content)

        row = conn.execute(
            f"{_ENTRY_SELECT} WHERE e.id = ? {_ENTRY_GROUP}",
            (entry_id,),
        ).fetchone()
        return row_to_entry(row)


@router.delete("/{entry_id}", status_code=204)
def delete_entry(entry_id: int):
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM entries WHERE id = ?", (entry_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Entry not found")
        conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
