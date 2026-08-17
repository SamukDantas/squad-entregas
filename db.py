import os
import sqlite3
from datetime import datetime, timezone

_DB_PADRAO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tasks.db")


def db_path():
    """Caminho do banco, resolvido a cada chamada.

    Lido no import, `TASKS_DB_PATH` só valeria se definida antes de importar
    este módulo — quem a definisse depois seguiria no caminho padrão, sem
    aviso.
    """
    return os.environ.get("TASKS_DB_PATH", _DB_PADRAO)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT    NOT NULL CHECK(length(title) BETWEEN 1 AND 100),
    description TEXT,
    status      TEXT    NOT NULL DEFAULT 'pending'
                CHECK(status IN ('pending','in_progress','done')),
    -- Sem DEFAULT: os carimbos vêm do código, em ISO-8601 com timezone (_now).
    -- Um DEFAULT (datetime('now')) gravaria 'YYYY-MM-DD HH:MM:SS' na mesma
    -- coluna, e a origem do valor decidiria o formato. Sem ele, um INSERT que
    -- esqueça as colunas falha alto em vez de gravar no outro formato.
    created_at  TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL
);
"""


def get_connection():
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    try:
        conn.execute(_SCHEMA)
        conn.commit()
    finally:
        conn.close()


def _now():
    return datetime.now(timezone.utc).isoformat()


def list_tasks(status=None, page=1, page_size=10):
    conditions = []
    params = []
    if status is not None:
        conditions.append("status = ?")
        params.append(status)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    offset = (page - 1) * page_size

    conn = get_connection()
    try:
        total = conn.execute(f"SELECT COUNT(*) FROM tasks {where}", params).fetchone()[
            0
        ]
        rows = conn.execute(
            f"SELECT * FROM tasks {where} ORDER BY id ASC LIMIT ? OFFSET ?",
            params + [page_size, offset],
        ).fetchall()
        return [dict(row) for row in rows], total
    finally:
        conn.close()


def get_task(task_id):
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def create_task(title, description, status):
    now = _now()
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO tasks (title, description, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (title, description, status, now, now),
        )
        conn.commit()
        task_id = cur.lastrowid
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return dict(row)
    finally:
        conn.close()


def update_task(task_id, title, description, status):
    now = _now()
    conn = get_connection()
    try:
        cur = conn.execute(
            "UPDATE tasks SET title = ?, description = ?, status = ?, updated_at = ? "
            "WHERE id = ?",
            (title, description, status, now, task_id),
        )
        conn.commit()
        if cur.rowcount == 0:
            return None
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return dict(row)
    finally:
        conn.close()


def delete_task(task_id):
    conn = get_connection()
    try:
        cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()
