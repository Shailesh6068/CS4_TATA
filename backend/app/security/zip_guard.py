import os
import zipfile
from pathlib import Path
from fastapi import HTTPException
from backend.app.config import settings

MAX_UNCOMPRESSED_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024 * 3  # e.g. 150MB max
MAX_ZIP_RATIO = 50.0  # Zip bomb ratio threshold

def safe_extract_zip(zip_path: str, destination_dir: str) -> list[str]:
    """
    Safely inspects and extracts a zip archive.
    Guards against:
    - Zip Bombs (excessive uncompressed size and extreme compression ratios)
    - Path Traversal (Zip Slip / directory escape)
    - Executable / forbidden binaries
    """
    dest = Path(destination_dir).resolve()
    dest.mkdir(parents=True, exist_ok=True)
    
    extracted_files = []
    total_uncompressed = 0
    
    with zipfile.ZipFile(zip_path, "r") as zf:
        # Check compression ratio & total size
        for info in zf.infolist():
            total_uncompressed += info.file_size
            if info.compress_size > 0:
                ratio = info.file_size / info.compress_size
                if ratio > MAX_ZIP_RATIO and info.file_size > 10 * 1024 * 1024:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Security alert: Potential Zip Bomb detected in entry '{info.filename}'."
                    )
        
        if total_uncompressed > MAX_UNCOMPRESSED_BYTES:
            raise HTTPException(
                status_code=400,
                detail=f"Archive total uncompressed size ({total_uncompressed / (1024*1024):.1f} MB) exceeds maximum allowed limit."
            )
        
        # Verify all paths are strictly inside target directory
        for member in zf.namelist():
            # Normalize member path
            norm_member = os.path.normpath(member)
            if norm_member.startswith("..") or os.path.isabs(norm_member) or ":\\" in norm_member:
                raise HTTPException(
                    status_code=400,
                    detail=f"Security alert: Malicious path traversal attempted in entry '{member}'."
                )
            
            target_path = (dest / norm_member).resolve()
            if not str(target_path).startswith(str(dest)):
                raise HTTPException(
                    status_code=400,
                    detail=f"Security alert: Path traversal escape attempt in entry '{member}'."
                )
                
            # Filter forbidden extensions
            ext = target_path.suffix.lower()
            if ext in settings.FORBIDDEN_EXTENSIONS:
                continue  # Skip forbidden binary files
                
            if member.endswith("/"):
                target_path.mkdir(parents=True, exist_ok=True)
            else:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member) as source, open(target_path, "wb") as target:
                    target.write(source.read())
                extracted_files.append(str(target_path))
                
    return extracted_files
