from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.schemas.api_schemas import (
    CodeReviewRequest, SecurityReviewRequest, MisraReviewRequest,
    ReviewResponse, DiffReviewRequest, DiffReviewResponse,
    CodeExplanationRequest, CodeExplanationResponse
)
from backend.app.services.review_service import review_service

router = APIRouter(prefix="", tags=["Reviews"])

@router.post("/review/code", response_model=ReviewResponse)
def execute_code_review(req: CodeReviewRequest, db: Session = Depends(get_db)):
    return review_service.run_review(
        db=db,
        project_id=req.project_id,
        review_type="GENERAL",
        file_paths=req.file_paths,
        code_snippet=req.code_snippet,
        file_name=req.file_name or "snippet.cpp",
        use_rag=req.use_rag
    )

@router.post("/review/security", response_model=ReviewResponse)
def execute_security_review(req: SecurityReviewRequest, db: Session = Depends(get_db)):
    return review_service.run_review(
        db=db,
        project_id=req.project_id,
        review_type="SECURITY",
        file_paths=req.file_paths,
        code_snippet=req.code_snippet,
        file_name=req.file_name or "snippet.cpp",
        use_rag=req.use_rag
    )

@router.post("/review/misra", response_model=ReviewResponse)
def execute_misra_review(req: MisraReviewRequest, db: Session = Depends(get_db)):
    return review_service.run_review(
        db=db,
        project_id=req.project_id,
        review_type="MISRA",
        file_paths=req.file_paths,
        code_snippet=req.code_snippet,
        file_name=req.file_name or "ecu_core.cpp",
        use_rag=True,
        enabled_rules=req.enabled_rules
    )

@router.post("/review/diff", response_model=DiffReviewResponse)
def execute_diff_review(req: DiffReviewRequest):
    return review_service.review_diff(
        project_id=req.project_id,
        before_code=req.before_code,
        after_code=req.after_code,
        git_diff=req.git_diff,
        file_name=req.file_name or "diff.patch"
    )

@router.post("/explain/code", response_model=CodeExplanationResponse)
def execute_code_explanation(req: CodeExplanationRequest):
    return review_service.explain_code(
        project_id=req.project_id,
        file_path=req.file_path,
        code_snippet=req.code_snippet,
        mode=req.mode,
        target_symbol=req.target_symbol
    )
