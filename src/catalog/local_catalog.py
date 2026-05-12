from pathlib import Path
from typing import TypedDict
import hashlib
from config import CHUNK_SIZE_BYTES


class CatalogEntry(TypedDict):
    """
    Schema for a shared file entry.
    Tracks metadata including the unique file hash, filename, and size in bytes.
    """

    file_id: str
    name: str
    size: int


def compute_file_id(filepath: Path) -> str:
    """
    Generates a unique SHA-256 hash of a file to serve as its network identifier.
    Reads the file in configured chunk sizes to maintain efficiency for larger files.
    """
    sha256 = hashlib.sha256()

    with filepath.open("rb") as file:
        while chunk := file.read(CHUNK_SIZE_BYTES):
            sha256.update(chunk)

    return sha256.hexdigest()


def build_local_catalog(shared_folder: str) -> list[CatalogEntry]:
    """
    Scan the shared folder and return catalog entries.

    Each entry contains:
    - file_id (SHA-256 hash)
    - name (file name)
    - size (bytes)
    """
    catalog: list[CatalogEntry] = []
    folder_path = Path(shared_folder)

    if not folder_path.exists():
        return catalog

    for path in folder_path.iterdir():
        if path.is_file():
            entry: CatalogEntry = {
                "file_id": compute_file_id(path),
                "name": path.name,
                "size": path.stat().st_size,
            }
            catalog.append(entry)

    return catalog
