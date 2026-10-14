from backend.app.analyzers.fusion_engine import fuse_findings

def test_findings_fusion():
    llm_findings = [
        {
            "finding_code": "SEC-001",
            "category": "Security",
            "severity": "HIGH",
            "confidence": "HIGH",
            "file": "test.cpp",
            "line_start": 20,
            "issue": "Buffer overflow in copy",
            "evidence": "memcpy(...)",
            "explanation": "Unchecked DLC length",
            "recommendation": "Check bounds"
        }
    ]

    static_findings = [
        {
            "rule_id": "MISRA-C-21.6",
            "analyzer": "CPPMisraAnalyzer",
            "category": "Security",
            "severity": "HIGH",
            "line": 20,
            "message": "Unsafe buffer copy function",
            "snippet": "memcpy(...)"
        },
        {
            "rule_id": "MISRA-C-21.3",
            "analyzer": "CPPMisraAnalyzer",
            "category": "MISRA",
            "severity": "MEDIUM",
            "line": 45,
            "message": "Dynamic memory allocation detected",
            "snippet": "malloc(100)"
        }
    ]

    fused = fuse_findings(llm_findings, static_findings, file_path="test.cpp")
    
    # 1. Matching finding on line 20 should have source_type = COMBINED
    matched = [f for f in fused if f.get("line_start") == 20]
    assert len(matched) == 1
    assert matched[0]["source_type"] == "COMBINED"

    # 2. Unmatched static finding on line 45 should be preserved as STATIC_ANALYZER
    unmatched_static = [f for f in fused if f.get("line_start") == 45]
    assert len(unmatched_static) == 1
    assert unmatched_static[0]["source_type"] == "STATIC_ANALYZER"
