from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from ..database import get_db
from .entries import _ENTRY_SELECT, _ENTRY_GROUP, row_to_entry

router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: str = "general"


class ProjectUpdate(BaseModel):
    status: str


def row_to_project(row, entry_count: int = 0) -> dict:
    keys = row.keys() if hasattr(row, "keys") else []
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "category": row["category"],
        "status": row["status"] if "status" in keys else "active",
        "completedAt": row["completed_at"] if "completed_at" in keys else None,
        "createdAt": row["created_at"],
        "entryCount": entry_count,
    }


@router.get("")
def list_projects(status: Optional[str] = Query(default=None)):
    with get_db() as conn:
        if status == "archived":
            where = "WHERE p.status = 'archived'"
        elif status == "completed":
            where = "WHERE p.status = 'completed'"
        elif status == "active":
            where = "WHERE p.status = 'active'"
        elif status == "all":
            where = ""
        else:
            where = "WHERE p.status != 'archived'"

        rows = conn.execute(
            f"""
            SELECT p.*, COUNT(e.id) as entry_count
            FROM projects p
            LEFT JOIN entries e ON e.project_id = p.id
            {where}
            GROUP BY p.id
            ORDER BY p.created_at DESC
            """
        ).fetchall()
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "description": r["description"],
                "category": r["category"],
                "status": r["status"] if "status" in r.keys() else "active",
                "completedAt": r["completed_at"] if "completed_at" in r.keys() else None,
                "createdAt": r["created_at"],
                "entryCount": r["entry_count"],
            }
            for r in rows
        ]


@router.post("", status_code=201)
def create_project(body: ProjectCreate):
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO projects (name, description, category) VALUES (?, ?, ?)",
            (body.name, body.description, body.category),
        )
        row = conn.execute(
            "SELECT * FROM projects WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
        return row_to_project(row)


@router.get("/{project_id}")
def get_project(project_id: int):
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT p.*, COUNT(e.id) as entry_count
            FROM projects p
            LEFT JOIN entries e ON e.project_id = p.id
            WHERE p.id = ?
            GROUP BY p.id
            """,
            (project_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Project not found")
        return row_to_project(row, row["entry_count"])


@router.patch("/{project_id}")
def update_project_status(project_id: int, body: ProjectUpdate):
    allowed = {"active", "completed", "archived"}
    if body.status not in allowed:
        raise HTTPException(status_code=400, detail=f"status must be one of {allowed}")
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Project not found")

        completed_at = None
        if body.status == "completed":
            completed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        conn.execute(
            "UPDATE projects SET status = ?, completed_at = ? WHERE id = ?",
            (body.status, completed_at, project_id),
        )
        updated = conn.execute(
            """
            SELECT p.*, COUNT(e.id) as entry_count
            FROM projects p
            LEFT JOIN entries e ON e.project_id = p.id
            WHERE p.id = ?
            GROUP BY p.id
            """,
            (project_id,),
        ).fetchone()
        return row_to_project(updated, updated["entry_count"])


@router.get("/{project_id}/entries")
def get_project_entries(project_id: int):
    with get_db() as conn:
        proj = conn.execute(
            "SELECT id FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        rows = conn.execute(
            f"{_ENTRY_SELECT} WHERE e.project_id = ? {_ENTRY_GROUP} ORDER BY e.date DESC",
            (project_id,),
        ).fetchall()
        return [row_to_entry(r) for r in rows]


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int):
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Project not found")
        conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
