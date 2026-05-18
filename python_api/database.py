import sqlite3
import os
import json
from contextlib import contextmanager

DB_PATH = os.environ.get("DB_PATH", "journal.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def get_db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


TAG_COLORS = [
    "#ef4444", "#f97316", "#eab308", "#22c55e", "#06b6d4",
    "#3b82f6", "#8b5cf6", "#ec4899", "#14b8a6", "#f59e0b",
    "#10b981", "#6366f1",
]


def _migrate_project_status(conn):
    try:
        conn.execute("ALTER TABLE projects ADD COLUMN status TEXT NOT NULL DEFAULT 'active'")
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE projects ADD COLUMN completed_at TEXT DEFAULT NULL")
    except Exception:
        pass


def _migrate_entries_embeddings(conn):
    """Add embedding columns for RAG semantic search."""
    for stmt in (
        "ALTER TABLE entries ADD COLUMN embedding TEXT DEFAULT NULL",
        "ALTER TABLE entries ADD COLUMN embedding_provider TEXT DEFAULT NULL",
        "ALTER TABLE entries ADD COLUMN embedding_model TEXT DEFAULT NULL",
    ):
        try:
            conn.execute(stmt)
        except Exception:
            pass


def _migrate_entries_title(conn):
    """Add title column. Old entries left NULL — UI falls back to first line."""
    try:
        conn.execute("ALTER TABLE entries ADD COLUMN title TEXT DEFAULT NULL")
    except Exception:
        pass


def _migrate_tags_from_json(conn):
    entries = conn.execute(
        "SELECT id, tags FROM entries WHERE tags IS NOT NULL AND tags != '[]' "
        "AND id NOT IN (SELECT DISTINCT log_id FROM log_tags)"
    ).fetchall()
    for entry in entries:
        try:
            tag_names = json.loads(entry["tags"])
        except Exception:
            continue
        for name in tag_names:
            name = name.strip()
            if not name:
                continue
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
                (entry["id"], tag_id),
            )


def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                category TEXT NOT NULL DEFAULT 'general',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                content TEXT NOT NULL,
                project_id INTEGER NOT NULL,
                template TEXT NOT NULL DEFAULT 'freeform',
                mood INTEGER,
                tags TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_entries_project_id ON entries(project_id);
            CREATE INDEX IF NOT EXISTS idx_entries_date ON entries(date);

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                color TEXT NOT NULL DEFAULT '#6366f1'
            );

            CREATE TABLE IF NOT EXISTS log_tags (
                log_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                PRIMARY KEY (log_id, tag_id),
                FOREIGN KEY (log_id) REFERENCES entries(id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_log_tags_log_id ON log_tags(log_id);
        """)

        row = conn.execute("SELECT COUNT(*) as c FROM projects").fetchone()
        if row["c"] == 0:
            conn.execute(
                "INSERT INTO projects (name, description, category) VALUES (?, ?, ?)",
                ("個人成長", "追蹤個人學習與成長歷程", "general"),
            )
            conn.execute(
                "INSERT INTO projects (name, description, category) VALUES (?, ?, ?)",
                ("專案開發", "工程開發日誌與技術筆記", "engineering"),
            )
            conn.execute(
                "INSERT INTO entries (date, content, project_id, template, mood, tags) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    "2026-05-01",
                    "【今日目標】\n完成 API 基礎架構設計\n\n【完成事項】\n- 設計資料庫 schema\n- 研究 FastAPI 最佳實踐\n\n【遇到瓶頸】\n SQLite 並發處理需要調整\n\n【明日計畫】\n實作 CRUD API 端點",
                    2,
                    "engineering",
                    4,
                    '["FastAPI", "資料庫", "架構"]',
                ),
            )
            conn.execute(
                "INSERT INTO entries (date, content, project_id, template, mood, tags) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    "2026-05-02",
                    "【今日重點】\n閱讀《深度工作力》第三章\n\n【心得筆記】\n- 專注時段建議 90 分鐘為一個循環\n- 環境設計對專注力影響極大\n\n【行動項目】\n明天嘗試番茄鐘工作法",
                    1,
                    "office",
                    3,
                    '["閱讀", "專注力", "生產力"]',
                ),
            )
        _migrate_project_status(conn)
        _migrate_entries_embeddings(conn)
        _migrate_entries_title(conn)
        _migrate_tags_from_json(conn)
