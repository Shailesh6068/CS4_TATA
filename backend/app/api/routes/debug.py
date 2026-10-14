from fastapi import APIRouter
from backend.app.schemas.api_schemas import (
    DebugAnalyzeRequest, DebugAnalyzeResponse,
    LogAnalysisRequest, LogAnalysisResponse
)
from backend.app.services.debugging_service import debugging_service

router = APIRouter(prefix="", tags=["Debugging"])

@router.post("/debug/analyze", response_model=DebugAnalyzeResponse)
def analyze_debugging_incident(req: DebugAnalyzeRequest):
    return debugging_service.analyze_debug(req)

@router.post("/logs/analyze", response_model=LogAnalysisResponse)
def analyze_runtime_logs(req: LogAnalysisRequest):
    return debugging_service.analyze_logs(req)
