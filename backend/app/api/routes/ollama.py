from typing import List
from fastapi import APIRouter, HTTPException
from backend.app.schemas.api_schemas import (
    OllamaStatusResponse, OllamaChangeModelRequest
)
from backend.app.services.ollama_service import ollama_service

router = APIRouter(prefix="", tags=["Ollama"])

@router.get("/ollama/status", response_model=OllamaStatusResponse)
def get_ollama_status():
    stat = ollama_service.check_status()
    return OllamaStatusResponse(
        is_connected=stat["is_connected"],
        base_url=stat["base_url"],
        active_model=stat["active_model"],
        available_models=stat["available_models"],
        gpu_accelerated=stat.get("gpu_accelerated", False),
        message=stat["message"]
    )

@router.get("/ollama/models", response_model=List[str])
def list_available_models():
    return ollama_service.get_available_models()

@router.post("/ollama/model")
def switch_active_model(req: OllamaChangeModelRequest):
    available = ollama_service.get_available_models()
    if available and not any(m == req.model_name or m.startswith(req.model_name) or req.model_name.startswith(m.split(":")[0]) for m in available):
        raise HTTPException(
            status_code=400,
            detail=f"Model '{req.model_name}' is not installed in local Ollama. Available models: {', '.join(available)}"
        )
    ollama_service.set_active_model(req.model_name)
    return {"message": f"Active model switched to {req.model_name}", "active_model": req.model_name}
