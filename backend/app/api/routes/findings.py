from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.db_models import Finding, FindingComment
from backend.app.schemas.api_schemas import (
    FindingResponse, FindingUpdate, FindingVerificationRequest, FindingVerificationResponse
)
from backend.app.services.static_analysis_service import static_analysis_service
from backend.app.services.ollama_service import ollama_service
from backend.app.utils.audit_logger import log_audit_event

router = APIRouter(prefix="", tags=["Findings"])

@router.get("/findings", response_model=List[FindingResponse])
def get_findings(
    project_id: Optional[int] = None,
    review_id: Optional[int] = None,
    severity: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Finding)
    if project_id:
        query = query.filter(Finding.project_id == project_id)
    if review_id:
        query = query.filter(Finding.review_id == review_id)
    if severity:
        query = query.filter(Finding.severity == severity.upper())
    if category:
        query = query.filter(Finding.category == category)
    if status:
        query = query.filter(Finding.status == status.upper())

    findings = query.order_by(Finding.id.desc()).all()
    return findings

@router.patch("/findings/{finding_id}", response_model=FindingResponse)
def update_finding(finding_id: int, update: FindingUpdate, db: Session = Depends(get_db)):
    finding = db.query(Finding).filter(Finding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    old_status = finding.status
    if update.status:
        finding.status = update.status.upper()

    if update.comment:
        comment_rec = FindingComment(
            finding_id=finding.id,
            comment=update.comment
        )
        db.add(comment_rec)

    # Single commit for both status update and optional comment (atomic)
    db.commit()
    db.refresh(finding)

    log_audit_event(
        db,
        "FINDING_UPDATED",
        project_id=finding.project_id,
        target_type="FINDING",
        target_id=str(finding.id),
        details={"old_status": old_status, "new_status": finding.status}
    )
    return finding

@router.post("/findings/{finding_id}/verify", response_model=FindingVerificationResponse)
def verify_finding_fix(finding_id: int, req: FindingVerificationRequest, db: Session = Depends(get_db)):
    finding = db.query(Finding).filter(Finding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    # 1. Deterministic re-analysis of updated code
    file_path = finding.file_path or "snippet.cpp"
    static_res = static_analysis_service.analyze_file(file_path, req.updated_code)
    still_present_static = any(
        f.get("rule_id") == finding.finding_code for f in static_res.get("findings", [])
    )

    # 2. LLM verification prompt
    prompt = f"""
VERIFY FIX FOR FINDING:
Finding Code: {finding.finding_code}
Issue: {finding.issue}
Original Problematic Evidence: {finding.evidence}

UPDATED CODE TO VERIFY:
{req.updated_code}

Determine if the fix correctly resolves the issue without introducing new vulnerabilities.
Respond strictly in this format:
RESULT: RESOLVED or NOT_RESOLVED
EXPLANATION: <1-2 sentences on whether the issue was fixed>
"""
    explanation = ""
    resolved = False
    try:
        resp = ollama_service.generate(prompt=prompt, system_prompt="You are a strict code fix verifier.")
        if "RESULT: RESOLVED" in resp.upper() and not still_present_static:
            resolved = True
        explanation = resp
    except Exception:
        resolved = not still_present_static
        explanation = "Deterministic re-analysis showed rule violation is no longer present." if resolved else "Issue still flagged by static rules."

    prev_status = finding.status
    if resolved:
        finding.status = "VERIFIED"
        db.commit()
        log_audit_event(db, "FIX_VERIFIED", project_id=finding.project_id, target_id=str(finding.id))
        return FindingVerificationResponse(
            finding_id=finding.id,
            previous_status=prev_status,
            new_status="VERIFIED",
            verification_passed=True,
            explanation=explanation,
            rechecked_evidence="No longer detected in revised code block."
        )
    else:
        return FindingVerificationResponse(
            finding_id=finding.id,
            previous_status=prev_status,
            new_status=prev_status,
            verification_passed=False,
            explanation=explanation,
            rechecked_evidence=finding.evidence
        )
