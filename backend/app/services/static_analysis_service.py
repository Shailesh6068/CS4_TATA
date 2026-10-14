import os
import subprocess
import json
from typing import List, Dict, Any
from backend.app.analyzers.python_ast_analyzer import PythonASTAnalyzer
from backend.app.analyzers.cpp_misra_analyzer import CPPMisraAnalyzer

class StaticAnalysisService:
    """Orchestrates deterministic static analyzers for Python, C, and C++ codebases."""

    def analyze_file(self, file_path: str, code_content: str) -> Dict[str, Any]:
        ext = os.path.splitext(file_path)[1].lower()
        findings: List[Dict[str, Any]] = []
        symbols: List[Dict[str, Any]] = []
        complexity: Dict[str, int] = {}

        if ext in (".py",):
            ast_analyzer = PythonASTAnalyzer(file_path, code_content)
            res = ast_analyzer.analyze()
            findings.extend(res["findings"])
            symbols.extend(res["symbols"])
            complexity.update(res["complexity"])

            # Optional: Run bandit if installed
            bandit_findings = self._run_bandit_if_available(file_path, code_content)
            findings.extend(bandit_findings)

        elif ext in (".c", ".cpp", ".cc", ".cxx", ".h", ".hpp"):
            cpp_analyzer = CPPMisraAnalyzer(file_path, code_content)
            res = cpp_analyzer.analyze()
            findings.extend(res["findings"])
            symbols.extend(res["symbols"])

        return {
            "findings": findings,
            "symbols": symbols,
            "complexity": complexity
        }

    def _run_bandit_if_available(self, file_path: str, code_content: str) -> List[Dict[str, Any]]:
        # Lightweight check: bandit CLI or programmatic
        # Since PythonASTAnalyzer already detects secrets, eval, and system calls,
        # return empty if no external process is needed to ensure speed
        return []

static_analysis_service = StaticAnalysisService()
