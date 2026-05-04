import sqlite3
import os
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
