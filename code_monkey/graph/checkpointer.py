import logging
import os
import sqlite3
from dataclasses import dataclass, field

import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

DEFAULT_DB_PATH = ".codemonkey/checkpoints.db"
DEFAULT_THREAD_ID = "session"


@dataclass
class CheckpointerResult:
    checkpointer: AsyncSqliteSaver | None
    errors: list[str] = field(default_factory=list)


def _delete_db_files(db_path: str) -> None:
    logging.debug("Deleting checkpoint database files at %s", db_path)
    for path in [db_path, f"{db_path}-shm", f"{db_path}-wal"]:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass


async def _open_checkpointer(db_path: str) -> AsyncSqliteSaver:
    conn = await aiosqlite.connect(db_path)
    logging.debug("Connected to checkpoint database at %s", db_path)
    checkpointer = AsyncSqliteSaver(conn)
    await checkpointer.setup()
    logging.debug("Checkpoint database setup complete")
    return checkpointer


async def make_checkpointer() -> CheckpointerResult:
    db_path = os.environ.get("CODEMONKEY_DB_PATH", DEFAULT_DB_PATH)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    logging.debug("Using checkpoint database at %s", db_path)
    try:
        return CheckpointerResult(checkpointer=await _open_checkpointer(db_path))
    except sqlite3.DatabaseError as e:
        error = f"Checkpoint database is corrupted ({e}). Clearing state and starting fresh."
        _delete_db_files(db_path)
        try:
            return CheckpointerResult(
                checkpointer=await _open_checkpointer(db_path), errors=[error]
            )
        except sqlite3.DatabaseError as e2:
            return CheckpointerResult(
                checkpointer=None,
                errors=[
                    error,
                    f"Failed to recreate checkpoint database ({e2}). Session will not be persisted.",
                ],
            )
