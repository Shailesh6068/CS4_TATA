import json
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from backend.app.models.db_models import AuditLog

def log_audit_event(
    db: Session,
    action: str,
    project_id: int | None = None,
    user_id: int | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    details: dict | None = None
):
    """
    Persists an auditable event to the relational database.
    Redacts any sensitive tokens/credentials from details before writing.
    """
    safe_details = {}
    if details:
        for k, v in details.items():
            k_lower = str(k).lower()
            if any(term in k_lower for term in ["key", "secret", "password", "token", "auth"]):
                safe_details[k] = "[REDACTED]"
            else:
                safe_details[k] = str(v)[:1000]

    log_entry = AuditLog(
        user_id=user_id,
        project_id=project_id,
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id else None,
        details_json=json.dumps(safe_details) if safe_details else None,
        timestamp=datetime.now(timezone.utc)
    )
    db.add(log_entry)
    db.commit()
