from backend.app.analyzers.python_ast_analyzer import PythonASTAnalyzer
from backend.app.analyzers.cpp_misra_analyzer import CPPMisraAnalyzer

def test_python_ast_analyzer():
    py_code = """
api_key = "secret_token_12345"

def dangerous_exec(user_input):
    eval(user_input)
"""
    analyzer = PythonASTAnalyzer("test.py", py_code)
    res = analyzer.analyze()
    findings = res["findings"]
    rules = [f["rule_id"] for f in findings]

    assert "SEC-HARDCODED-SECRET" in rules
    assert "SEC-DANGEROUS-EVAL" in rules

def test_cpp_misra_analyzer():
    cpp_code = """
#include <string.h>
#include <stdlib.h>

void process() {
    char* buf = (char*)malloc(128);
    strcpy(buf, "hello");
}
"""
    analyzer = CPPMisraAnalyzer("test.cpp", cpp_code)
    res = analyzer.analyze()
    findings = res["findings"]
    rules = [f["rule_id"] for f in findings]

    assert "MISRA-C-21.3" in rules  # Dynamic memory
    assert "MISRA-C-21.6" in rules  # strcpy
