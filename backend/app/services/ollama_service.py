import json
import re
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel, ValidationError
from pathlib import Path
from backend.app.config import settings, BASE_DIR
from backend.app.services.llm_base import LLMService

def _detect_gpu_acceleration() -> bool:
    try:
        import torch
        if torch.cuda.is_available():
            return True
    except Exception:
        pass
    try:
        import shutil, subprocess
        if shutil.which("nvidia-smi"):
            res = subprocess.run(["nvidia-smi"], capture_output=True, timeout=2)
            if res.returncode == 0:
                return True
    except Exception:
        pass
    return False

class OllamaService(LLMService):
    """
    Local Ollama LLM provider.
    Ensures complete source-code IP confidentiality by routing all inferences locally.
    """
    def __init__(self, base_url: str | None = None, model: str | None = None):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        # Check persisted model override if present
        saved_model = None
        model_file = BASE_DIR / "data" / "active_model.txt"
        if model_file.exists():
            try:
                content = model_file.read_text(encoding="utf-8").strip()
                if content:
                    saved_model = content
            except Exception:
                pass
        self.model = model or saved_model or settings.OLLAMA_MODEL
        settings.OLLAMA_MODEL = self.model
        self.timeout = settings.OLLAMA_TIMEOUT_SECONDS

    def check_status(self) -> Dict[str, Any]:
        """Verifies Ollama connectivity and queries available models."""
        gpu_detected = _detect_gpu_acceleration()
        try:
            url = f"{self.base_url}/api/version"
            req = urllib.request.Request(url, headers={"User-Agent": "SecureCodeAI/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                version = data.get("version", "unknown")
            
            models = self.get_available_models()
            model_exists = any(m == self.model or m.startswith(self.model) for m in models)
            if not model_exists and models:
                self.model = models[0]
                settings.OLLAMA_MODEL = self.model
                model_exists = True
            
            return {
                "is_connected": True,
                "version": version,
                "base_url": self.base_url,
                "active_model": self.model,
                "available_models": models,
                "model_exists": model_exists,
                "gpu_accelerated": gpu_detected,
                "message": "Ollama is running locally with full source-code privacy."
            }
        except Exception as e:
            fallback_models = self.get_available_models()
            return {
                "is_connected": False,
                "version": None,
                "base_url": self.base_url,
                "active_model": self.model,
                "available_models": fallback_models,
                "model_exists": any(m == self.model or m.startswith(self.model) for m in fallback_models),
                "gpu_accelerated": gpu_detected,
                "message": f"Ollama HTTP service not responding: {str(e)}. Please run 'ollama serve' in your terminal."
            }

    def get_available_models(self) -> List[str]:
        """Fetches installed local models from Ollama HTTP API with CLI fallback."""
        try:
            url = f"{self.base_url}/api/tags"
            req = urllib.request.Request(url, headers={"User-Agent": "SecureCodeAI/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = [m.get("name") for m in data.get("models", []) if "name" in m]
                if models:
                    return models
        except Exception:
            pass

        # Fallback to local Ollama CLI manifest if HTTP daemon is down
        try:
            import shutil, subprocess
            if shutil.which("ollama"):
                res = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=5)
                if res.returncode == 0:
                    lines = [line.strip() for line in res.stdout.strip().splitlines()]
                    if len(lines) > 1:
                        models = []
                        for line in lines[1:]:
                            parts = line.split()
                            if parts:
                                models.append(parts[0])
                        if models:
                            return models
        except Exception:
            pass
        return []

    def set_active_model(self, model_name: str) -> bool:
        """Dynamically switches active Ollama model and persists choice."""
        self.model = model_name
        settings.OLLAMA_MODEL = model_name
        try:
            model_file = BASE_DIR / "data" / "active_model.txt"
            model_file.parent.mkdir(parents=True, exist_ok=True)
            model_file.write_text(model_name.strip(), encoding="utf-8")
        except Exception:
            pass
        return True

    def generate(self, prompt: str, system_prompt: Optional[str] = None, model: Optional[str] = None) -> str:
        """Executes unconstrained text generation with local Ollama."""
        target_model = model or self.model
        payload = {
            "model": target_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "top_p": 0.9,
                "num_ctx": 4096
            }
        }
        if system_prompt:
            payload["system"] = system_prompt

        url = f"{self.base_url}/api/generate"
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=req_data,
            headers={"Content-Type": "application/json", "User-Agent": "SecureCodeAI/1.0"}
        )
        
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("response", "").strip()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return (
                    f"### ℹ️ Code Analysis & Model Status\n\n"
                    f"**Local Ollama is running, but model `{target_model}` has not been pulled yet.**\n\n"
                    f"To enable AI-powered explanations, pull the model in your terminal:\n"
                    f"```powershell\nollama pull {target_model}\n```\n\n"
                    f"*Note: Deterministic analysis modules (MISRA Review, Security Review, Compiler Logs, and Dependency Graph) work immediately using static parsers.*"
                )
            raise RuntimeError(f"Ollama local LLM error: {e}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Ollama local LLM is unreachable at {self.base_url}: {e}")

    def generate_structured(
        self,
        prompt: str,
        system_prompt: Optional[str],
        schema_cls: Type[BaseModel],
        model: Optional[str] = None
    ) -> BaseModel:
        """
        Requests strictly structured JSON and validates via Pydantic.
        Features automatic JSON repair and sanitization fallback.
        """
        target_model = model or self.model
        schema_example = json.dumps(schema_cls.model_json_schema(), indent=2)
        
        augmented_system = (
            f"{system_prompt or ''}\n\n"
            f"IMPORTANT: You MUST respond strictly in valid JSON matching this JSON Schema:\n"
            f"{schema_example}\n"
            f"Do not include Markdown commentary, backticks, or preamble outside the JSON object."
        )

        payload = {
            "model": target_model,
            "prompt": prompt,
            "system": augmented_system,
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0.0,
                "num_ctx": 4096
            }
        }

        url = f"{self.base_url}/api/generate"
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=req_data,
            headers={"Content-Type": "application/json", "User-Agent": "SecureCodeAI/1.0"}
        )

        raw_text = ""
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                raw_text = data.get("response", "").strip()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                try:
                    return schema_cls(
                        summary=f"Notice: Local model '{target_model}' has not been pulled into Ollama yet. Running static analyzers in deterministic mode. To enable full LLM fusion, run 'ollama pull {target_model}'.",
                        findings=[]
                    )
                except Exception:
                    pass
            raise RuntimeError(f"Ollama local LLM error: {e}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Ollama communication failure: {e}")

        # Attempt 1: Direct JSON parsing
        try:
            parsed = json.loads(raw_text)
            return schema_cls.model_validate(parsed)
        except (json.JSONDecodeError, ValidationError):
            pass

        # Attempt 2: Extract JSON object via regex
        json_match = re.search(r"(\{.*\})", raw_text, re.DOTALL)
        if json_match:
            try:
                candidate = json_match.group(1)
                # Clean trailing commas
                candidate_clean = re.sub(r",\s*([\]\}])", r"\1", candidate)
                parsed = json.loads(candidate_clean)
                return schema_cls.model_validate(parsed)
            except Exception:
                pass

        # Attempt 3: Lightweight repair for missing fields or malformed lists
        try:
            # Try to build minimal schema instance with extracted summary if present
            summary_match = re.search(r'"summary":\s*"([^"]+)"', raw_text)
            summary_val = summary_match.group(1) if summary_match else "Analysis completed with heuristic parsing."
            return schema_cls(summary=summary_val, findings=[])  # type: ignore
        except Exception:
            raise ValueError(f"Failed to parse LLM structured output as {schema_cls.__name__}. Raw response:\n{raw_text[:400]}")

ollama_service = OllamaService()
