"""Hash computation utilities for file change detection."""

import hashlib
from pathlib import Path


def compute_file_hash(filepath: Path | str) -> str:
    """Compute SHA-256 hash of a file for change detection.

    Args:
        filepath: Path to the file (Path object or string)

    Returns:
        Hexadecimal digest of the file's SHA-256 hash

    Raises:
        OSError: If the file cannot be read
    """
    path = Path(filepath)
    with open(path, "rb") as f:
        digest = hashlib.file_digest(f, "sha256")
    return digest.hexdigest()
