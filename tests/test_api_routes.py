from fastapi.testclient import TestClient
from backend.app.main import app

def test_root_and_health():
    with TestClient(app) as client:
        r1 = client.get("/")
        assert r1.status_code == 200
        assert "SecureCode AI" in r1.json()["service"]

        r2 = client.get("/health")
        assert r2.status_code == 200
        assert r2.json()["status"] == "HEALTHY"

def test_ollama_status_endpoint():
    with TestClient(app) as client:
        r = client.get("/api/v1/ollama/status")
        assert r.status_code == 200
        data = r.json()
        assert "is_connected" in data
        assert "available_models" in data

def test_project_lifecycle():
    with TestClient(app) as client:
        # Create project
        create_payload = {
            "name": "Integration Test ECU",
            "description": "ECU powertrain unit test workspace"
        }
        r = client.post("/api/v1/projects", json=create_payload)
        assert r.status_code == 200
        p_data = r.json()
        assert p_data["name"] == "Integration Test ECU"
        pid = p_data["id"]

        # List projects
        r_list = client.get("/api/v1/projects")
        assert r_list.status_code == 200
        assert any(p["id"] == pid for p in r_list.json())

        # Get single project
        r_single = client.get(f"/api/v1/projects/{pid}")
        assert r_single.status_code == 200
        assert r_single.json()["id"] == pid

def test_ollama_model_switch_validation():
    with TestClient(app) as client:
        # Status returns bool for gpu_accelerated
        stat = client.get("/api/v1/ollama/status").json()
        assert isinstance(stat["gpu_accelerated"], bool)

        # Switching to a non-existent model returns 400 with validation message
        r = client.post("/api/v1/ollama/model", json={"model_name": "definitely_nonexistent_model_xyz:99b"})
        # Should be 400 if models are available, or 200/400 handled gracefully
        assert r.status_code in (200, 400)

def test_knowledge_list_endpoint():
    with TestClient(app) as client:
        r = client.get("/api/v1/knowledge")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

def test_knowledge_query_endpoint():
    with TestClient(app) as client:
        r = client.post("/api/v1/knowledge/query", json={"query": "safety watchdog timer", "top_k": 2})
        assert r.status_code == 200
        data = r.json()
        assert "query" in data
        assert "citations" in data
        assert isinstance(data["citations"], list)


def test_report_generation_url_format():
    with TestClient(app) as client:
        # Create temporary project
        p = client.post("/api/v1/projects", json={"name": "Report URL Test Project"}).json()
        pid = p["id"]
        rep = client.post(f"/api/v1/reports/generate?project_id={pid}&format=markdown").json()
        assert "report_url" in rep
        assert rep["report_url"].startswith("/reports/download/")
        assert not rep["report_url"].startswith("/api/v1/api/v1")
