from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from backend.app.database import get_db
from backend.app.models.db_models import AuditLog, User
from backend.app.schemas.api_schemas import AuditLogResponse

router = APIRouter(prefix="", tags=["Audit Logs"])

@router.get("/audit/logs", response_model=List[AuditLogResponse])
def get_audit_logs(
    project_id: Optional[int] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    query = db.query(AuditLog).options(joinedload(AuditLog.user))
    if project_id:
        query = query.filter(AuditLog.project_id == project_id)
    
    logs = query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
    resp = []
    for l in logs:
        u_name = l.user.username if l.user else "engineer"
        resp.append(AuditLogResponse(
            id=l.id,
            user=u_name,
            action=l.action,
            target_type=l.target_type,
            target_id=l.target_id,
            details=l.details_json,
            timestamp=l.timestamp
        ))
    return resp
