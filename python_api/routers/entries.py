import json
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from ..database import get_db

router = APIRouter(prefix="/entries", tags=["entries"])


class EntryCreate(BaseModel):
    date: str
    content: str
    projectId: int
    template: str = "freeform"
    mood: Optional[int] = None
    tags: list[str] = []


class EntryUpdate(BaseModel):
    content: Optional[str] = None
    mood: Optional[int] = None
    tags: Optional[list[str]] = None


def row_to_entry(row) -> dict:
    tags = json.loads(row["tags"]) if row["tags"] else []
    return {
        "id": row["id"],
        "date": row["date"],
        "content": row["content"],
        "projectId": row["project_id"],
        "projectName": row["project_name"] if "project_name" in row.keys() else "",
        "template": row["template"],
        "mood": row["mood"],
        "tags": tags,
        "createdAt": row["created_at"],
    }


@router.get("")
def list_entries(
    projectId: Optional[int] = Query(None),
    limit: int = Query(50),
    offset: int = Query(0),
):
    with get_db() as conn:
        if projectId:
            rows = conn.execute(
                """
                SELECT e.*, p.name as project_name
                FROM entries e
                JOIN projects p ON p.id = e.project_id
                WHERE e.project_id = ?
                ORDER BY e.date DESC, e.created_at DESC
                LIMIT ? OFFSET ?
                """,
                (projectId, limit, offset),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT e.*, p.name as project_name
                FROM entries e
                JOIN projects p ON p.id = e.project_id
                ORDER BY e.date DESC, e.created_at DESC
                LIMIT ? OFFSET ?
                """,
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
            "INSERT INTO entries (date, content, project_id, template, mood, tags) VALUES (?, ?, ?, ?, ?, ?)",
            (
                body.date,
                body.content,
                body.projectId,
                body.template,
                body.mood,
                json.dumps(body.tags, ensure_ascii=False),
            ),
        )
        row = conn.execute(
            """
            SELECT e.*, p.name as project_name
            FROM entries e
            JOIN projects p ON p.id = e.project_id
            WHERE e.id = ?
            """,
            (cur.lastrowid,),
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
                """
                SELECT e.*, p.name as project_name
                FROM entries e
                JOIN projects p ON p.id = e.project_id
                WHERE e.project_id = ?
                ORDER BY e.date DESC LIMIT 5
                """,
                (projectId,),
            ).fetchall()
        else:
            recent_rows = conn.execute(
                """
                SELECT e.*, p.name as project_name
                FROM entries e
                JOIN projects p ON p.id = e.project_id
                ORDER BY e.date DESC LIMIT 5
                """
            ).fetchall()

        by_project = conn.execute(
            """
            SELECT p.id as project_id, p.name as project_name, COUNT(e.id) as count
            FROM projects p
            LEFT JOIN entries e ON e.project_id = p.id
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
            """
            SELECT e.*, p.name as project_name
            FROM entries e
            JOIN projects p ON p.id = e.project_id
            WHERE e.id = ?
            """,
            (entry_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Entry not found")
        return row_to_entry(row)


@router.put("/{entry_id}")
def update_entry(entry_id: int, body: EntryUpdate):
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM entries WHERE id = ?", (entry_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Entry not found")

        updates = []
        params = []
        if body.content is not None:
            updates.append("content = ?")
            params.append(body.content)
        if body.mood is not None:
            updates.append("mood = ?")
            params.append(body.mood)
        if body.tags is not None:
            updates.append("tags = ?")
            params.append(json.dumps(body.tags, ensure_ascii=False))

        if updates:
            params.append(entry_id)
            conn.execute(
                f"UPDATE entries SET {', '.join(updates)} WHERE id = ?", params
            )

        row = conn.execute(
            """
            SELECT e.*, p.name as project_name
            FROM entries e
            JOIN projects p ON p.id = e.project_id
            WHERE e.id = ?
            """,
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
