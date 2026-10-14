import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import ConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "SecureCode AI"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"
    
    # Storage & DB
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'data' / 'securecode.db'}")
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", str(BASE_DIR / "data" / "uploads"))
    CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", str(BASE_DIR / "data" / "chroma"))
    REPORTS_DIR: str = os.getenv("REPORTS_DIR", str(BASE_DIR / "data" / "reports"))
    
    # Ollama Local LLM Configuration (Strictly Local)
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    OLLAMA_TIMEOUT_SECONDS: int = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "90"))
    
    # Embeddings & RAG
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    CHUNK_SIZE: int = 600
    CHUNK_OVERLAP: int = 100
    TOP_K_RETRIEVAL: int = 4
    
    # Security Policies
    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: set[str] = {
        ".c", ".cpp", ".cc", ".cxx", ".h", ".hpp",
        ".py", ".java", ".js", ".ts",
        ".txt", ".log", ".json", ".yaml", ".yml", ".xml", ".md", ".pdf"
    }
    FORBIDDEN_EXTENSIONS: set[str] = {
        ".exe", ".dll", ".so", ".bin", ".o", ".a", ".out", ".pyc", ".class"
    }
    ENABLE_LOCAL_PRIVACY_ENFORCEMENT: bool = True
    CONFIDENCE_THRESHOLD: float = 0.65
    
    # JWT / Auth placeholders (RBAC ready)
    JWT_SECRET: str = "securecode-secret-key-automotive-local-only-2026"
    ALGORITHM: str = "HS256"

settings = Settings()

# Ensure mandatory directories exist
for p in [Path(settings.UPLOAD_DIR), Path(settings.CHROMA_PERSIST_DIR), Path(settings.REPORTS_DIR)]:
    p.mkdir(parents=True, exist_ok=True)
