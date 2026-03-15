import os
import sqlite3
from dataclasses import dataclass, field

from langgraph.checkpoint.sqlite import SqliteSaver

DEFAULT_DB_PATH = ".codemonkey/checkpoints.db"
DEFAULT_THREAD_ID = "session"


@dataclass
class CheckpointerResult:
    checkpointer: SqliteSaver | None
    errors: list[str] = field(default_factory=list)


def _delete_db_files(db_path: str) -> None:
    for path in [db_path, f"{db_path}-shm", f"{db_path}-wal"]:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass


def _open_checkpointer(db_path: str) -> SqliteSaver:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    checkpointer.setup()
    return checkpointer


def make_checkpointer() -> CheckpointerResult:
    db_path = os.environ.get("CODEMONKEY_DB_PATH", DEFAULT_DB_PATH)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    try:
        return CheckpointerResult(checkpointer=_open_checkpointer(db_path))
    except sqlite3.DatabaseError as e:
        error = f"Checkpoint database is corrupted ({e}). Clearing state and starting fresh."
        _delete_db_files(db_path)
        try:
            return CheckpointerResult(
                checkpointer=_open_checkpointer(db_path), errors=[error]
            )
        except sqlite3.DatabaseError as e2:
            return CheckpointerResult(
                checkpointer=None,
                errors=[
                    error,
                    f"Failed to recreate checkpoint database ({e2}). Session will not be persisted.",
                ],
            )
