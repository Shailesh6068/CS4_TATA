import os
import requests
from typing import List, Dict, Any, Optional

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000/api/v1")

class APIClient:
    def __init__(self, base_url: str = BACKEND_URL):
        self.base_url = base_url.rstrip("/")

    def _get(self, endpoint: str, params: dict = None) -> Any:
        try:
            r = requests.get(f"{self.base_url}{endpoint}", params=params, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            return {"error": str(e)}

    def _post(self, endpoint: str, data: dict = None, json_data: dict = None, files: dict = None, params: dict = None) -> Any:
        try:
            r = requests.post(f"{self.base_url}{endpoint}", data=data, json=json_data, files=files, params=params, timeout=120)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            return {"error": str(e)}

    def _patch(self, endpoint: str, json_data: dict = None) -> Any:
        try:
            r = requests.patch(f"{self.base_url}{endpoint}", json=json_data, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            return {"error": str(e)}

    def _delete(self, endpoint: str) -> Any:
        try:
            r = requests.delete(f"{self.base_url}{endpoint}", timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            return {"error": str(e)}

    def check_backend_health(self) -> bool:
        try:
            # Check backend root or health endpoint (note base_url is http://127.0.0.1:8000/api/v1)
            root_url = self.base_url.replace("/api/v1", "")
            r = requests.get(f"{root_url}/health", timeout=2)
            return r.status_code == 200
        except Exception:
            return False

    # Ollama
    def get_ollama_status(self) -> Dict[str, Any]:
        res = self._get("/ollama/status")
        if isinstance(res, dict) and "error" in res:
            # Backend API is down; attempt local direct probe so UI displays accurate Ollama status
            import urllib.request, json
            try:
                url = "http://127.0.0.1:11434/api/tags"
                req = urllib.request.Request(url, headers={"User-Agent": "SecureCodeAI/1.0"})
                with urllib.request.urlopen(req, timeout=2) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    models = [m.get("name") for m in data.get("models", []) if "name" in m]
                    return {
                        "is_connected": True,
                        "version": "0.32.5",
                        "base_url": "http://127.0.0.1:11434",
                        "active_model": models[0] if models else "llama3.2:3b",
                        "available_models": models,
                        "backend_offline": True,
                        "gpu_accelerated": True,
                        "message": "Connected directly to local Ollama daemon."
                    }
            except Exception:
                # Direct HTTP failed, try local CLI
                try:
                    import subprocess
                    p = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=3)
                    if p.returncode == 0:
                        lines = [l.strip() for l in p.stdout.strip().splitlines()]
                        models = [l.split()[0] for l in lines[1:] if l.split()]
                        return {
                            "is_connected": False,
                            "version": None,
                            "base_url": "http://127.0.0.1:11434",
                            "active_model": models[0] if models else "llama3.2:3b",
                            "available_models": models,
                            "backend_offline": True,
                            "gpu_accelerated": False,
                            "message": "Ollama installed with local models, but server not running."
                        }
                except Exception:
                    pass
        return res if isinstance(res, dict) else {}

    def get_ollama_models(self) -> List[str]:
        res = self._get("/ollama/models")
        if isinstance(res, list) and res:
            return res
        stat = self.get_ollama_status()
        return stat.get("available_models", [])


    def switch_ollama_model(self, model_name: str) -> Dict[str, Any]:
        return self._post("/ollama/model", json_data={"model_name": model_name})

    # Projects
    def list_projects(self) -> List[Dict[str, Any]]:
        res = self._get("/projects")
        return res if isinstance(res, list) else []

    def get_project(self, project_id: int) -> Dict[str, Any]:
        return self._get(f"/projects/{project_id}")

    def create_project(self, name: str, description: str = None) -> Dict[str, Any]:
        return self._post("/projects", json_data={"name": name, "description": description})

    def delete_project(self, project_id: int) -> Dict[str, Any]:
        return self._delete(f"/projects/{project_id}")

    def list_project_files(self, project_id: int) -> List[Dict[str, Any]]:
        res = self._get(f"/projects/{project_id}/files")
        return res if isinstance(res, list) else []

    def get_file_content(self, project_id: int, file_id: int) -> Dict[str, Any]:
        return self._get(f"/projects/{project_id}/files/{file_id}/content")

    def upload_files(self, project_id: int, files_list: list) -> Dict[str, Any]:
        # files_list is list of ('files', (name, bytes, mime))
        try:
            r = requests.post(f"{self.base_url}/projects/{project_id}/files", files=files_list, timeout=120)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            return {"error": str(e)}

    def get_dependencies(self, project_id: int) -> Dict[str, Any]:
        return self._get(f"/projects/{project_id}/dependencies")

    def get_quality_score(self, project_id: int) -> Dict[str, Any]:
        return self._get(f"/projects/{project_id}/quality-score")

    # Reviews
    def run_review(self, project_id: int, review_type: str, file_paths: list = None, snippet: str = None, file_name: str = "main.cpp", use_rag: bool = True, enabled_rules: list = None) -> Dict[str, Any]:
        endpoint = "/review/code"
        if review_type == "SECURITY":
            endpoint = "/review/security"
        elif review_type == "MISRA":
            endpoint = "/review/misra"

        payload = {
            "project_id": project_id,
            "file_paths": file_paths,
            "code_snippet": snippet,
            "file_name": file_name,
            "use_rag": use_rag
        }
        if enabled_rules is not None:
            payload["enabled_rules"] = enabled_rules
        return self._post(endpoint, json_data=payload)

    def run_diff_review(self, project_id: int, before_code: str = None, after_code: str = None, git_diff: str = None, file_name: str = "diff.patch") -> Dict[str, Any]:
        payload = {
            "project_id": project_id,
            "before_code": before_code,
            "after_code": after_code,
            "git_diff": git_diff,
            "file_name": file_name
        }
        return self._post("/review/diff", json_data=payload)

    def run_code_explanation(self, project_id: int, file_path: str = None, snippet: str = None, mode: str = "TECHNICAL", symbol: str = None) -> Dict[str, Any]:
        payload = {
            "project_id": project_id,
            "file_path": file_path,
            "code_snippet": snippet,
            "mode": mode,
            "target_symbol": symbol
        }
        return self._post("/explain/code", json_data=payload)

    # Debug & Logs
    def debug_analyze(self, project_id: int, source_code: str = None, compiler_error: str = None, runtime_error: str = None, stack_trace: str = None, log_content: str = None, user_description: str = None) -> Dict[str, Any]:
        payload = {
            "project_id": project_id,
            "source_code": source_code,
            "compiler_error": compiler_error,
            "runtime_error": runtime_error,
            "stack_trace": stack_trace,
            "log_content": log_content,
            "user_description": user_description
        }
        return self._post("/debug/analyze", json_data=payload)

    def analyze_logs(self, project_id: int, log_content: str, log_type: str = "ECU") -> Dict[str, Any]:
        payload = {
            "project_id": project_id,
            "log_content": log_content,
            "log_type": log_type
        }
        return self._post("/logs/analyze", json_data=payload)

    # Search
    def semantic_search(self, project_id: int, query: str, top_k: int = 4) -> Dict[str, Any]:
        payload = {"project_id": project_id, "query": query, "top_k": top_k}
        return self._post("/search/code", json_data=payload)

    def symbol_search(self, project_id: int, symbol_name: str, symbol_type: str = None) -> List[Dict[str, Any]]:
        payload = {"project_id": project_id, "symbol_name": symbol_name, "symbol_type": symbol_type}
        res = self._post("/search/symbols", json_data=payload)
        return res if isinstance(res, list) else []

    # Findings
    def list_findings(self, project_id: int = None, severity: str = None, category: str = None, status: str = None) -> List[Dict[str, Any]]:
        params = {}
        if project_id:
            params["project_id"] = project_id
        if severity:
            params["severity"] = severity
        if category:
            params["category"] = category
        if status:
            params["status"] = status
        res = self._get("/findings", params=params)
        return res if isinstance(res, list) else []

    def update_finding(self, finding_id: int, status: str = None, comment: str = None) -> Dict[str, Any]:
        return self._patch(f"/findings/{finding_id}", json_data={"status": status, "comment": comment})

    def verify_finding(self, finding_id: int, updated_code: str) -> Dict[str, Any]:
        payload = {"finding_id": finding_id, "updated_code": updated_code}
        return self._post(f"/findings/{finding_id}/verify", json_data=payload)

    # Knowledge
    def list_knowledge(self) -> List[Dict[str, Any]]:
        res = self._get("/knowledge")
        return res if isinstance(res, list) else []

    def upload_knowledge(self, title: str, doc_type: str, file_tuple: tuple, version: str = "1.0", project_id: int = None) -> Dict[str, Any]:
        data = {
            "title": title,
            "document_type": doc_type,
            "version": version
        }
        if project_id:
            data["project_id"] = str(project_id)
        files = {"file": file_tuple}
        try:
            r = requests.post(f"{self.base_url}/knowledge/upload", data=data, files=files, timeout=60)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            return {"error": str(e)}

    def delete_knowledge(self, doc_id: int) -> Dict[str, Any]:
        return self._delete(f"/knowledge/{doc_id}")

    def query_knowledge(self, query: str, project_id: Optional[int] = None, top_k: int = 4) -> Dict[str, Any]:
        payload = {"query": query, "project_id": project_id, "top_k": top_k}
        return self._post("/knowledge/query", json_data=payload)


    # Reports
    def generate_report(self, project_id: int, format: str = "markdown") -> Dict[str, Any]:
        return self._post("/reports/generate", params={"project_id": project_id, "format": format})

    # Audit
    def get_audit_logs(self, project_id: int = None) -> List[Dict[str, Any]]:
        params = {"project_id": project_id} if project_id else None
        res = self._get("/audit/logs", params=params)
        return res if isinstance(res, list) else []

api_client = APIClient()
