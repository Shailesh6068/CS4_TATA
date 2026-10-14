"""
Tests for:
- Findings CRUD lifecycle (filter, PATCH status, verify fix)
- Audit log endpoint
- Report generation (JSON and CSV formats)
- Project dependency graph endpoint
"""
import json
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models.db_models import Finding, Review


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def project_with_finding(client):
    """Creates a project, uploads a file, seeds a DB finding, returns (pid, fid)."""
    p = client.post("/api/v1/projects", json={"name": "FindingsTest ECU", "description": "findings test"}).json()
    pid = p["id"]

    c_code = b"""
#include <string.h>
#include <stdlib.h>

void process(const char* input) {
    char buf[32];
    strcpy(buf, input);
    void* p = malloc(128);
}
"""
    up = client.post(
        f"/api/v1/projects/{pid}/files",
        files=[("files", ("process.c", c_code, "text/plain"))]
    )
    assert up.status_code == 200

    db = SessionLocal()
    try:
        review = Review(
            project_id=pid,
            review_type="SECURITY",
            status="COMPLETED",
            summary="Static analysis seed review",
            overall_risk="HIGH",
            score=72.0,
            security_score=60.0,
            correctness_score=80.0,
            maintainability_score=75.0
        )
        db.add(review)
        db.commit()
        db.refresh(review)

        finding = Finding(
            review_id=review.id,
            project_id=pid,
            finding_code="SEC-STRCPY-001",
            category="Security",
            severity="CRITICAL",
            confidence="HIGH",
            source_type="STATIC_ANALYZER",
            file_path="process.c",
            line_start=7,
            line_end=7,
            issue="Unbounded strcpy() detected — buffer overflow (MISRA C:2012 Rule 21.6).",
            evidence="strcpy(buf, input);",
            explanation="strcpy does not check destination buffer bounds.",
            recommendation="Replace with strncpy with explicit bound.",
            suggested_fix="strncpy(buf, input, sizeof(buf) - 1);",
            status="OPEN"
        )
        db.add(finding)
        db.commit()
        db.refresh(finding)
        fid = finding.id
    finally:
        db.close()

    return pid, fid


# ---------------------------------------------------------------------------
# Findings Filtering Tests
# ---------------------------------------------------------------------------

def test_findings_list_all(client):
    r = client.get("/api/v1/findings")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_findings_filter_by_project(client, project_with_finding):
    pid, fid = project_with_finding
    r = client.get(f"/api/v1/findings?project_id={pid}")
    assert r.status_code == 200
    findings = r.json()
    assert len(findings) >= 1
    assert all(f["project_id"] == pid for f in findings)


def test_findings_filter_by_severity(client, project_with_finding):
    pid, fid = project_with_finding
    r = client.get(f"/api/v1/findings?project_id={pid}&severity=CRITICAL")
    assert r.status_code == 200
    results = r.json()
    assert all(f["severity"] == "CRITICAL" for f in results)


def test_findings_filter_by_status(client, project_with_finding):
    pid, fid = project_with_finding
    r = client.get(f"/api/v1/findings?project_id={pid}&status=OPEN")
    assert r.status_code == 200
    assert all(f["status"] == "OPEN" for f in r.json())


# ---------------------------------------------------------------------------
# Finding PATCH (Status Update + Comment)
# ---------------------------------------------------------------------------

def test_patch_finding_status_to_confirmed(client, project_with_finding):
    pid, fid = project_with_finding
    r = client.patch(
        f"/api/v1/findings/{fid}",
        json={"status": "CONFIRMED", "comment": "Verified manually — reproducible in fuzzing."}
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "CONFIRMED"
    assert data["id"] == fid


def test_patch_finding_status_to_in_progress(client, project_with_finding):
    pid, fid = project_with_finding
    r = client.patch(f"/api/v1/findings/{fid}", json={"status": "IN_PROGRESS"})
    assert r.status_code == 200
    assert r.json()["status"] == "IN_PROGRESS"


def test_patch_finding_404(client):
    r = client.patch("/api/v1/findings/999999", json={"status": "FIXED"})
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Finding Fix Verification
# ---------------------------------------------------------------------------

def test_verify_finding_fix_deterministic(client, project_with_finding):
    pid, fid = project_with_finding
    fixed_code = """
#include <string.h>

void process(const char* input) {
    char buf[32];
    strncpy(buf, input, sizeof(buf) - 1);
    buf[sizeof(buf) - 1] = '\0';
}
"""
    r = client.post(
        f"/api/v1/findings/{fid}/verify",
        json={"updated_code": fixed_code}
    )
    assert r.status_code == 200
    data = r.json()
    assert "finding_id" in data
    assert "verification_passed" in data
    assert isinstance(data["verification_passed"], bool)
    assert data["finding_id"] == fid


def test_verify_finding_404(client):
    r = client.post("/api/v1/findings/999999/verify", json={"updated_code": "int x = 1;"})
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Audit Log Tests
# ---------------------------------------------------------------------------

def test_audit_logs_list(client):
    r = client.get("/api/v1/audit/logs")
    assert r.status_code == 200
    logs = r.json()
    assert isinstance(logs, list)
    assert len(logs) >= 1
    first = logs[0]
    assert "action" in first
    assert "timestamp" in first


def test_audit_logs_limit(client):
    r = client.get("/api/v1/audit/logs?limit=3")
    assert r.status_code == 200
    assert len(r.json()) <= 3


# ---------------------------------------------------------------------------
# Report Generation (JSON and CSV formats)
# ---------------------------------------------------------------------------

def test_report_json_format(client, project_with_finding):
    pid, _ = project_with_finding
    r = client.post(f"/api/v1/reports/generate?project_id={pid}&format=json")
    assert r.status_code == 200
    data = r.json()
    assert "report_url" in data
    assert "content" in data
    parsed = json.loads(data["content"])
    assert parsed["project_id"] == pid
    assert "findings" in parsed
    assert isinstance(parsed["findings"], list)


def test_report_csv_format(client, project_with_finding):
    pid, _ = project_with_finding
    r = client.post(f"/api/v1/reports/generate?project_id={pid}&format=csv")
    assert r.status_code == 200
    data = r.json()
    assert "content" in data
    csv_lines = data["content"].strip().splitlines()
    assert len(csv_lines) >= 1
    assert "Finding Code" in csv_lines[0]


def test_report_invalid_format(client, project_with_finding):
    pid, _ = project_with_finding
    r = client.post(f"/api/v1/reports/generate?project_id={pid}&format=docx")
    assert r.status_code == 422


def test_report_nonexistent_project(client):
    r = client.post("/api/v1/reports/generate?project_id=999999&format=markdown")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Project Dependency Graph Endpoint
# ---------------------------------------------------------------------------

def test_dependency_graph_endpoint(client, project_with_finding):
    pid, _ = project_with_finding
    r = client.get(f"/api/v1/projects/{pid}/dependencies")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, dict)


# ---------------------------------------------------------------------------
# Quality Score Endpoint
# ---------------------------------------------------------------------------

def test_quality_score_endpoint(client, project_with_finding):
    pid, _ = project_with_finding
    r = client.get(f"/api/v1/projects/{pid}/quality-score")
    assert r.status_code == 200
    data = r.json()
    # Score key may vary; find the numeric composite score
    score_val = None
    for key in ("composite_score", "score", "quality_score", "overall_score"):
        if key in data:
            score_val = float(data[key])
            break
    assert score_val is not None, f"No score key found in response: {data}"
    assert 0 <= score_val <= 100
