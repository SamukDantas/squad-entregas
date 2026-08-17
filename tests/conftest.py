import atexit
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

_TMP_DIR = Path(tempfile.mkdtemp(prefix="tasks-api-tests-"))
_DB_PATH = _TMP_DIR / "tasks.db"

# db.py lê TASKS_DB_PATH a cada conexão. Definindo aqui, o banco usado pela
# aplicação fica isolado em um diretório temporário durante toda a suíte.
os.environ["TASKS_DB_PATH"] = str(_DB_PATH)
atexit.register(shutil.rmtree, _TMP_DIR, ignore_errors=True)


@pytest.fixture(autouse=True)
def _clean_database():
    """Recria a tabela tasks antes de cada teste, garantindo isolamento."""
    import db

    conn = db.get_connection()
    try:
        conn.execute("DROP TABLE IF EXISTS tasks")
        conn.commit()
    finally:
        conn.close()

    db.init_db()

    conn = db.get_connection()
    try:
        # Garante que os IDs voltem a 1 em cada teste. A tabela sqlite_sequence
        # só existe quando o SQLite cria uma tabela com AUTOINCREMENT; por isso
        # o fallback silencioso.
        conn.execute("DELETE FROM sqlite_sequence WHERE name='tasks'")
        conn.commit()
    except sqlite3.OperationalError:
        pass
    finally:
        conn.close()

    yield
