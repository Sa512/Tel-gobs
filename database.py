"""
طبقة بسيطة فوق SQLite لتخزين:
- بيانات كل مستخدم (السيرة الذاتية بصيغة JSON)
- سجل محادثة المرشد المهني (آخر عدة رسائل فقط، عشان السياق)
"""
import json
import sqlite3
from contextlib import contextmanager

from config import DB_PATH


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                full_name TEXT,
                cv_data TEXT,          -- JSON يحتوي كل حقول السيرة الذاتية
                cv_pdf_path TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS advisor_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                role TEXT,             -- 'user' أو 'assistant'
                content TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)


def upsert_user(user_id: int, full_name: str = None):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO users (user_id, full_name) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET full_name=COALESCE(excluded.full_name, full_name)",
            (user_id, full_name),
        )


def save_cv_data(user_id: int, cv_data: dict):
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET cv_data=? WHERE user_id=?",
            (json.dumps(cv_data, ensure_ascii=False), user_id),
        )


def get_cv_data(user_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT cv_data FROM users WHERE user_id=?", (user_id,)
        ).fetchone()
        if row and row["cv_data"]:
            return json.loads(row["cv_data"])
        return None


def save_cv_pdf_path(user_id: int, path: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET cv_pdf_path=? WHERE user_id=?", (path, user_id)
        )


def get_cv_pdf_path(user_id: int) -> str | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT cv_pdf_path FROM users WHERE user_id=?", (user_id,)
        ).fetchone()
        return row["cv_pdf_path"] if row else None


def add_advisor_message(user_id: int, role: str, content: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO advisor_history (user_id, role, content) VALUES (?, ?, ?)",
            (user_id, role, content),
        )


def get_advisor_history(user_id: int, limit: int = 12) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT role, content FROM advisor_history WHERE user_id=? "
            "ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
