import hashlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def verify_file_hash(filepath: str, expected_file_id: str) -> bool:
    """
    Compute SHA-256 of the file at filepath and compare to expected_file_id.

    Returns True if they match, False on mismatch.
    On mismatch the file is deleted and the event is logged.
    """
    sha256 = hashlib.sha256()
    path = Path(filepath)

    try:
        with path.open("rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
    except OSError as e:
        logger.error(f"[HASH_CHECK] Could not read file '{filepath}': {e}")
        return False

    actual = sha256.hexdigest()

    if actual != expected_file_id:
        logger.warning(
            f"[HASH_CHECK] MISMATCH for '{filepath}' — "
            f"expected={expected_file_id!r}, got={actual!r}. "
            "Discarding file."
        )
        try:
            path.unlink()
        except OSError as e:
            logger.error(
                f"[HASH_CHECK] Failed to delete corrupt file '{filepath}': {e}"
            )
        return False

    logger.info(f"[HASH_CHECK] '{filepath}' verified OK (SHA-256 matches file_id).")
    return True
