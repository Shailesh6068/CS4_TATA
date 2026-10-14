import os
import re
from pathlib import Path
from fastapi import HTTPException
from backend.app.config import settings

SAFE_FILENAME_RE = re.compile(r"^[a-zA-Z0-9_\-\.\s\(\)]+$")

def validate_safe_filename(filename: str) -> str:
    """Sanitizes filename and checks for path traversal characters."""
    raw = str(filename).strip()
    if not raw or ".." in raw or "/" in raw or "\\" in raw or ":" in raw:
        raise HTTPException(status_code=400, detail="Invalid filename or path traversal detected.")
    base_name = os.path.basename(raw).strip()
    if not SAFE_FILENAME_RE.match(base_name):
        # Clean unsafe characters
        base_name = re.sub(r"[^a-zA-Z0-9_\-\.\s\(\)]", "_", base_name)
    return base_name

def validate_extension(filename: str) -> str:
    """Validates file extension against allowed engineering types."""
    ext = Path(filename).suffix.lower()
    if ext in settings.FORBIDDEN_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Forbidden binary or executable file extension: {ext}")
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file extension: {ext}")
    return ext

def is_text_file(content_bytes: bytes) -> bool:
    """Detects whether raw file bytes represent text or binary."""
    # Check for null bytes in initial sample
    sample = content_bytes[:4096]
    if b"\x00" in sample:
        return False
    return True
