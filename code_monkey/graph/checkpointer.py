import os
import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver

DEFAULT_DB_PATH = ".codemonkey/checkpoints.db"
DEFAULT_THREAD_ID = "session"


def make_checkpointer() -> SqliteSaver:
    db_path = os.environ.get("CODEMONKEY_DB_PATH", DEFAULT_DB_PATH)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    checkpointer.setup()
    return checkpointer
