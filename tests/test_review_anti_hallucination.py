import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.services.review_service import review_service

client = TestClient(app)

def test_review_clean_hello_world():
    db = SessionLocal()
    try:
        hw_code = """#include <iostream>
using namespace std;

int main() {
    cout << "Hello World";
    return 0;
}"""
        res = review_service.run_review(
            db=db,
            project_id=1,
            review_type="GENERAL",
            code_snippet=hw_code,
            file_name="snippet.cpp",
            use_rag=False
        )
        assert res.overall_risk == "LOW"
        assert len(res.findings) == 0
        assert res.score == 100.0
        assert "No vulnerabilities or defects detected" in res.summary
    finally:
        db.close()

def test_review_empty_code():
    db = SessionLocal()
    try:
        res = review_service.run_review(
            db=db,
            project_id=1,
            review_type="GENERAL",
            code_snippet="",
            file_name="snippet.cpp",
            use_rag=False
        )
        assert res.overall_risk == "LOW"
        assert len(res.findings) == 0
        assert "No source code provided" in res.summary
    finally:
        db.close()

def test_get_file_content_api():
    # Create project and upload a test file
    p_res = client.post("/api/v1/projects", json={"name": "TestContentProject"})
    assert p_res.status_code == 200
    pid = p_res.json()["id"]

    content = b"int add(int a, int b) { return a + b; }\n"
    up_res = client.post(
        f"/api/v1/projects/{pid}/files",
        files=[("files", ("math.cpp", content, "text/plain"))]
    )
    assert up_res.status_code == 200

    files = client.get(f"/api/v1/projects/{pid}/files").json()
    assert len(files) >= 1
    fid = files[0]["id"]

    c_res = client.get(f"/api/v1/projects/{pid}/files/{fid}/content")
    assert c_res.status_code == 200
    assert "int add(int a, int b)" in c_res.json()["content"]
