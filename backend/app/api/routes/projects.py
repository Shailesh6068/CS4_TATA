import os
import shutil
import hashlib
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.config import settings
from backend.app.models.db_models import Project, ProjectFile, FileSymbol, Finding
from backend.app.schemas.api_schemas import (
    ProjectCreate, ProjectResponse, FileResponse,
    ProjectQualityScoreResponse
)
from backend.app.security.sanitizer import validate_safe_filename, validate_extension, is_text_file
from backend.app.security.zip_guard import safe_extract_zip
from backend.app.services.static_analysis_service import static_analysis_service
from backend.app.services.rag_service import rag_service
from backend.app.services.dependency_service import dependency_service
from backend.app.services.complexity_service import complexity_service
from backend.app.utils.audit_logger import log_audit_event

router = APIRouter(prefix="", tags=["Projects"])

@router.post("/projects", response_model=ProjectResponse)
def create_project(project_in: ProjectCreate, db: Session = Depends(get_db)):
    existing = db.query(Project).filter(Project.name == project_in.name).first()
    if existing:
        return existing

    project = Project(
        name=project_in.name,
        description=project_in.description,
        repo_path="",
        is_active=True
    )
    db.add(project)
    db.flush()

    project_dir = os.path.join(settings.UPLOAD_DIR, str(project.id))
    os.makedirs(project_dir, exist_ok=True)
    project.repo_path = project_dir

    db.commit()
    db.refresh(project)
    
    log_audit_event(db, "PROJECT_CREATED", project_id=project.id, details={"name": project.name})
    return project

@router.get("/projects", response_model=List[ProjectResponse])
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(Project).all()
    resp = []
    for p in projects:
        f_count = db.query(ProjectFile).filter(ProjectFile.project_id == p.id).count()
        find_count = db.query(Finding).filter(Finding.project_id == p.id).count()
        item = ProjectResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            repo_path=p.repo_path,
            is_active=p.is_active,
            created_at=p.created_at,
            file_count=f_count,
            finding_count=find_count
        )
        resp.append(item)
    return resp

@router.get("/projects/{project_id}", response_model=ProjectResponse)
def get_project(project_id: int, db: Session = Depends(get_db)):
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    f_count = db.query(ProjectFile).filter(ProjectFile.project_id == p.id).count()
    find_count = db.query(Finding).filter(Finding.project_id == p.id).count()
    return ProjectResponse(
        id=p.id,
        name=p.name,
        description=p.description,
        repo_path=p.repo_path,
        is_active=p.is_active,
        created_at=p.created_at,
        file_count=f_count,
        finding_count=find_count
    )

@router.post("/projects/{project_id}/files")
async def upload_project_files(
    project_id: int,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    target_dir = os.path.join(settings.UPLOAD_DIR, str(project_id))
    os.makedirs(target_dir, exist_ok=True)
    
    indexed_files = []

    for upload_file in files:
        filename = validate_safe_filename(upload_file.filename or "file.txt")
        contents = await upload_file.read()

        if len(contents) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            raise HTTPException(status_code=400, detail=f"File {filename} exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit.")

        # Check if Zip Archive
        if filename.lower().endswith(".zip"):
            temp_zip = os.path.join(target_dir, f"_temp_{filename}")
            with open(temp_zip, "wb") as f:
                f.write(contents)
            try:
                extracted = safe_extract_zip(temp_zip, target_dir)
            finally:
                if os.path.exists(temp_zip):
                    os.remove(temp_zip)

            # Index all extracted files
            for ext_path in extracted:
                if os.path.isfile(ext_path):
                    with open(ext_path, "rb") as ef:
                        ef_bytes = ef.read()
                    if is_text_file(ef_bytes):
                        rel_path = os.path.relpath(ext_path, target_dir).replace("\\", "/")
                        text_content = ef_bytes.decode("utf-8", errors="ignore")
                        p_file = _index_and_save_file(db, project_id, rel_path, text_content, ef_bytes)
                        indexed_files.append(p_file.relative_path)

        else:
            # Single file upload — validate_extension raises HTTPException on forbidden extensions
            validate_extension(filename)
            if not is_text_file(contents):
                continue  # Skip binary files

            dest_path = os.path.join(target_dir, filename)
            with open(dest_path, "wb") as f:
                f.write(contents)

            text_content = contents.decode("utf-8", errors="ignore")
            p_file = _index_and_save_file(db, project_id, filename, text_content, contents)
            indexed_files.append(p_file.relative_path)

    log_audit_event(db, "FILES_UPLOADED", project_id=project_id, details={"count": len(indexed_files)})
    return {"message": f"Successfully ingested {len(indexed_files)} files.", "files": indexed_files}

def _index_and_save_file(db: Session, project_id: int, rel_path: str, content: str, raw_bytes: bytes) -> ProjectFile:
    filename = os.path.basename(rel_path)
    ext = os.path.splitext(filename)[1].lower()
    sha256 = hashlib.sha256(raw_bytes).hexdigest()
    lines = content.splitlines()

    lang = "cpp" if ext in (".cpp", ".c", ".h", ".hpp", ".cc") else ("python" if ext == ".py" else ext.strip("."))

    existing = db.query(ProjectFile).filter(
        ProjectFile.project_id == project_id,
        ProjectFile.relative_path == rel_path
    ).first()

    if existing:
        p_file = existing
        p_file.size_bytes = len(raw_bytes)
        p_file.line_count = len(lines)
        p_file.sha256_hash = sha256
        # Remove existing symbols
        db.query(FileSymbol).filter(FileSymbol.file_id == p_file.id).delete()
        # Persist the updated metadata (mirrors the new-file branch below)
        db.commit()
        db.refresh(p_file)
    else:
        p_file = ProjectFile(
            project_id=project_id,
            relative_path=rel_path,
            file_name=filename,
            extension=ext,
            size_bytes=len(raw_bytes),
            language=lang,
            line_count=len(lines),
            sha256_hash=sha256
        )
        db.add(p_file)
        db.commit()
        db.refresh(p_file)

    # Deterministic static analysis to extract symbols
    static_res = static_analysis_service.analyze_file(rel_path, content)
    for sym in static_res.get("symbols", []):
        db_sym = FileSymbol(
            file_id=p_file.id,
            symbol_name=sym["name"],
            symbol_type=sym["type"],
            line_start=sym.get("line_start", 1),
            line_end=sym.get("line_end", 1),
            signature=sym.get("signature")
        )
        db.add(db_sym)

    db.commit()

    # Index into ChromaDB for semantic search
    rag_service.index_code_file(project_id, rel_path, content)

    return p_file

@router.get("/projects/{project_id}/files", response_model=List[FileResponse])
def list_project_files(project_id: int, db: Session = Depends(get_db)):
    files = db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()
    return files

@router.get("/projects/{project_id}/files/{file_id}/content")
def get_project_file_content(project_id: int, file_id: int, db: Session = Depends(get_db)):
    pf = db.query(ProjectFile).filter(
        ProjectFile.project_id == project_id,
        ProjectFile.id == file_id
    ).first()
    if not pf:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Try project.repo_path first, then fallback to UPLOAD_DIR / str(project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    candidates = []
    if project and project.repo_path:
        candidates.append(os.path.join(project.repo_path, pf.relative_path))
    candidates.append(os.path.join(settings.UPLOAD_DIR, str(project_id), pf.relative_path))
    if project:
        candidates.append(os.path.join(settings.UPLOAD_DIR, project.name.replace(" ", "_"), pf.relative_path))

    content = ""
    found = False
    for path in candidates:
        if os.path.exists(path) and os.path.isfile(path):
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            found = True
            break

    if not found:
        raise HTTPException(status_code=404, detail="File content not found on local disk")

    return {
        "file_id": pf.id,
        "relative_path": pf.relative_path,
        "language": pf.language,
        "line_count": pf.line_count,
        "content": content
    }

@router.get("/projects/{project_id}/dependencies")
def get_project_dependencies(project_id: int, db: Session = Depends(get_db)):
    target_dir = os.path.join(settings.UPLOAD_DIR, str(project_id))
    file_map = {}
    if os.path.exists(target_dir):
        for root, _, f_names in os.walk(target_dir):
            for fn in f_names:
                ext = os.path.splitext(fn)[1].lower()
                if ext in settings.ALLOWED_EXTENSIONS:
                    fp = os.path.join(root, fn)
                    rel = os.path.relpath(fp, target_dir).replace("\\", "/")
                    try:
                        with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                            file_map[rel] = f.read()
                    except Exception:
                        pass
    return dependency_service.build_dependency_graph(file_map)

@router.get("/projects/{project_id}/quality-score", response_model=ProjectQualityScoreResponse)
def get_project_quality_score(project_id: int, db: Session = Depends(get_db)):
    files = db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()
    total_loc = sum(f.line_count for f in files)
    
    findings = db.query(Finding).filter(Finding.project_id == project_id).all()
    crit_count = sum(1 for f in findings if f.severity == "CRITICAL")
    high_count = sum(1 for f in findings if f.severity == "HIGH")

    # Approximate average complexity
    avg_complexity = 4.2
    return complexity_service.compute_quality_score(
        findings_count=len(findings),
        critical_count=crit_count,
        high_count=high_count,
        total_loc=max(1, total_loc),
        avg_complexity=avg_complexity
    )

@router.delete("/projects/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    p_name = project.name
    # Clean up disk files
    target_dirs = [
        os.path.join(settings.UPLOAD_DIR, str(project_id)),
        project.repo_path
    ]
    for d in target_dirs:
        if d and os.path.exists(d) and os.path.isdir(d):
            try:
                shutil.rmtree(d, ignore_errors=True)
            except Exception:
                pass

    db.delete(project)
    db.commit()
    return {"message": f"Project '{p_name}' (ID: {project_id}) deleted successfully."}
