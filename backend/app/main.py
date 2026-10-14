import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.config import settings
from backend.app.database import engine, Base, SessionLocal
from backend.app.models.db_models import User, ReviewRule
from backend.app.api.routes import (
    projects, review, debug, knowledge, search, findings, reports, ollama, audit
)

# Ensure DB schema tables exist
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB schema and seed tables
    Base.metadata.create_all(bind=engine)
    
    # Seed default user and rules
    db = SessionLocal()
    try:
        default_user = db.query(User).filter(User.username == "engineer").first()
        if not default_user:
            default_user = User(
                username="engineer",
                email="engineer@automotive.internal",
                role="ENGINEER"
            )
            admin_user = User(
                username="admin",
                email="admin@automotive.internal",
                role="ADMIN"
            )
            db.add_all([default_user, admin_user])
            db.commit()

        # Seed baseline rules if table is empty
        if db.query(ReviewRule).count() == 0:
            baseline_rules = [
                ReviewRule(
                    rule_id="MISRA-C-21.3",
                    standard="MISRA_C_2012",
                    name="Dynamic Memory Allocation Prohibition",
                    description="The memory allocation and deallocation functions shall not be used in safety-critical loops.",
                    severity="HIGH"
                ),
                ReviewRule(
                    rule_id="MISRA-C-21.6",
                    standard="MISRA_C_2012",
                    name="Unbounded I/O and Buffer Functions",
                    description="Standard library input/output functions (gets, sprintf, strcpy) shall not be used.",
                    severity="CRITICAL"
                ),
                ReviewRule(
                    rule_id="MISRA-C-11.4",
                    standard="MISRA_C_2012",
                    name="Unsafe Pointer Conversion",
                    description="A conversion should not be performed between a pointer to object type and a different pointer type.",
                    severity="HIGH"
                ),
                ReviewRule(
                    rule_id="CWE-798",
                    standard="CWE",
                    name="Hardcoded Credentials in ECU Firmware",
                    description="Credentials, tokens, or diagnostic secret keys must not be hardcoded in binary source.",
                    severity="HIGH"
                ),
                ReviewRule(
                    rule_id="AUTO-CAN-DLC-01",
                    standard="AUTOSAR",
                    name="CAN Frame Payload Bound Check",
                    description="CAN frame DLC length must be verified against destination buffer capacity before copy.",
                    severity="CRITICAL"
                )
            ]
            db.add_all(baseline_rules)
            db.commit()
    finally:
        db.close()
    
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Privacy-Preserving Local LLM-Powered Secure Code Debugging & Review Assistant for Automotive Engineering",
    lifespan=lifespan
)

# CORS configuration for Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers
api_prefix = settings.API_PREFIX
app.include_router(projects.router, prefix=api_prefix)
app.include_router(review.router, prefix=api_prefix)
app.include_router(debug.router, prefix=api_prefix)
app.include_router(knowledge.router, prefix=api_prefix)
app.include_router(search.router, prefix=api_prefix)
app.include_router(findings.router, prefix=api_prefix)
app.include_router(reports.router, prefix=api_prefix)
app.include_router(ollama.router, prefix=api_prefix)
app.include_router(audit.router, prefix=api_prefix)

@app.get("/")
def root():
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "privacy": "100% LOCAL PROCESSING (AIR-GAPPED READY)",
        "docs_url": "/docs",
        "api_prefix": settings.API_PREFIX
    }

@app.get("/health")
def health():
    return {"status": "HEALTHY", "engine": "FastAPI + Ollama"}
