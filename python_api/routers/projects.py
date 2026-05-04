import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from ..database import get_db

router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: str = "general"


def row_to_project(row, entry_count: int = 0) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "category": row["category"],
        "createdAt": row["created_at"],
        "entryCount": entry_count,
    }


@router.get("")
def list_projects():
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT p.*, COUNT(e.id) as entry_count
            FROM projects p
            LEFT JOIN entries e ON e.project_id = p.id
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
        return {
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "category": row["category"],
            "createdAt": row["created_at"],
            "entryCount": row["entry_count"],
        }


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int):
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Project not found")
        conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
