import pytest
from backend.app.analyzers.cpp_misra_analyzer import CPPMisraAnalyzer
from backend.app.analyzers.fusion_engine import fuse_findings

def test_strlen_heap_buffer_overflow_detection():
    code = """
void updateName(const char* vehicleName) {
    char* name = new char[strlen(vehicleName)];
    strcpy(name, vehicleName);
    delete[] name;
}
"""
    analyzer = CPPMisraAnalyzer("test.cpp", code)
    res = analyzer.analyze()
    rule_ids = [f["rule_id"] for f in res["findings"]]
    
    # Must catch strlen allocation defect and strcpy
    assert "MEM-STRLEN-ALLOC-01" in rule_ids
    assert "MISRA-C-21.6" in rule_ids

    strlen_finding = next(f for f in res["findings"] if f["rule_id"] == "MEM-STRLEN-ALLOC-01")
    assert strlen_finding["severity"] == "CRITICAL"
    assert strlen_finding["category"] == "MemorySafety"
    assert "strlen" in strlen_finding["root_cause"]
    assert "suggested_fix" in strlen_finding

def test_mismatched_delete_detection():
    code = """
class Packet {
public:
    int* data;
    Packet() {
        data = new int[50];
    }
    ~Packet() {
        delete data; // Mismatched scalar delete on array
    }
};
"""
    analyzer = CPPMisraAnalyzer("test.cpp", code)
    res = analyzer.analyze()
    rule_ids = [f["rule_id"] for f in res["findings"]]
    assert "MEM-MISMATCHED-DELETE-02" in rule_ids

def test_array_out_of_bounds_and_loop_off_by_one():
    code = """
void process() {
    int arr[10];
    for (int i = 0; i <= 10; i++) {
        arr[i] = i;
    }
    int x = arr[10];
}
"""
    analyzer = CPPMisraAnalyzer("test.cpp", code)
    res = analyzer.analyze()
    rule_ids = [f["rule_id"] for f in res["findings"]]
    assert "ARR-OFF-BY-ONE-LOOP-01" in rule_ids
    assert "ARR-OUT-OF-BOUNDS-01" in rule_ids

def test_use_after_free_and_double_free():
    code = """
void cleanup(char* ptr) {
    free(ptr);
    *ptr = 'A';
    free(ptr);
}
"""
    analyzer = CPPMisraAnalyzer("test.cpp", code)
    res = analyzer.analyze()
    rule_ids = [f["rule_id"] for f in res["findings"]]
    assert "MEM-USE-AFTER-FREE-01" in rule_ids
    assert "MEM-DOUBLE-FREE-01" in rule_ids

def test_assignment_in_conditional():
    code = """
void check(int x, int y) {
    if (x = y) {
        // ...
    }
}
"""
    analyzer = CPPMisraAnalyzer("test.cpp", code)
    res = analyzer.analyze()
    rule_ids = [f["rule_id"] for f in res["findings"]]
    assert "CORR-ASSIGN-IN-COND-01" in rule_ids

def test_sizeof_pointer_bug():
    code = """
void zeroBuffer(int* ptr) {
    memset(ptr, 0, sizeof(ptr));
}
"""
    analyzer = CPPMisraAnalyzer("test.cpp", code)
    res = analyzer.analyze()
    rule_ids = [f["rule_id"] for f in res["findings"]]
    assert "SEC-SIZEOF-POINTER-01" in rule_ids

def test_fusion_engine_deduplication_and_highest_severity():
    llm_findings = [
        {
            "finding_code": "SEC-001",
            "category": "MemorySafety",
            "severity": "HIGH",
            "confidence": "HIGH",
            "file": "test.cpp",
            "line_start": 5,
            "issue": "String copy without null terminator",
            "evidence": "strcpy(name, vehicleName);",
            "explanation": "Missing +1 byte",
            "recommendation": "Use strlen + 1"
        }
    ]
    static_findings = [
        {
            "rule_id": "MEM-STRLEN-ALLOC-01",
            "analyzer": "CPPMisraAnalyzer",
            "category": "MemorySafety",
            "severity": "CRITICAL",
            "line": 4,
            "message": "strlen() missing + 1",
            "snippet": "name = new char[strlen(vehicleName)];",
            "root_cause": "strlen does not count null terminator",
            "impact": "Heap buffer overflow",
            "standards": "CWE-131, CWE-120",
            "suggested_fix": "name = new char[strlen(vehicleName) + 1];"
        }
    ]

    fused = fuse_findings(llm_findings, static_findings, file_path="test.cpp")
    assert len(fused) == 1
    # Line 4 and Line 5 are within 2 lines -> fused!
    # Adopt higher severity: CRITICAL > HIGH
    assert fused[0]["severity"] == "CRITICAL"
    assert fused[0]["source_type"] == "COMBINED"
    assert "CWE-131" in fused[0]["explanation"]
