import ast
from typing import List, Dict, Any

SECRET_KEYWORDS = {"password", "secret", "token", "api_key", "apikey", "private_key", "auth_token"}

class PythonASTAnalyzer(ast.NodeVisitor):
    def __init__(self, filename: str, source_code: str):
        self.filename = filename
        self.source_code = source_code
        self.lines = source_code.splitlines()
        self.findings: List[Dict[str, Any]] = []
        self.symbols: List[Dict[str, Any]] = []
        self.complexity_map: Dict[str, int] = {}
        self.current_function = None

    def analyze(self) -> Dict[str, Any]:
        try:
            tree = ast.parse(self.source_code, filename=self.filename)
            self.visit(tree)
        except SyntaxError as e:
            self.findings.append({
                "rule_id": "SYNTAX-ERR",
                "analyzer": "PythonAST",
                "category": "Syntax",
                "severity": "CRITICAL",
                "line": e.lineno or 1,
                "message": f"Syntax error: {e.msg}",
                "snippet": self.lines[e.lineno - 1] if e.lineno and e.lineno <= len(self.lines) else ""
            })
        return {
            "findings": self.findings,
            "symbols": self.symbols,
            "complexity": self.complexity_map
        }

    def _get_line_snippet(self, lineno: int) -> str:
        if 1 <= lineno <= len(self.lines):
            return self.lines[lineno - 1].strip()
        return ""

    def visit_FunctionDef(self, node: ast.FunctionDef):
        prev_func = self.current_function
        self.current_function = node.name
        
        # Calculate cyclomatic complexity
        branch_count = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler, ast.With, ast.Assert)):
                branch_count += 1
            elif isinstance(child, ast.BoolOp):
                branch_count += len(child.values) - 1

        self.complexity_map[node.name] = branch_count
        line_start = node.lineno
        line_end = getattr(node, "end_lineno", line_start)
        
        self.symbols.append({
            "name": node.name,
            "type": "FUNCTION",
            "line_start": line_start,
            "line_end": line_end,
            "signature": f"def {node.name}({len(node.args.args)} args)"
        })

        if branch_count > 10:
            self.findings.append({
                "rule_id": "PY-COMPLEXITY",
                "analyzer": "PythonAST",
                "category": "Maintainability",
                "severity": "MEDIUM" if branch_count <= 15 else "HIGH",
                "line": line_start,
                "message": f"High cyclomatic complexity ({branch_count}) in function '{node.name}'.",
                "snippet": self._get_line_snippet(line_start)
            })

        self.generic_visit(node)
        self.current_function = prev_func

    def visit_ClassDef(self, node: ast.ClassDef):
        line_start = node.lineno
        line_end = getattr(node, "end_lineno", line_start)
        self.symbols.append({
            "name": node.name,
            "type": "CLASS",
            "line_start": line_start,
            "line_end": line_end,
            "signature": f"class {node.name}"
        })
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        # Detect hardcoded credentials
        for target in node.targets:
            if isinstance(target, ast.Name):
                var_name = target.id.lower()
                if any(kw in var_name for kw in SECRET_KEYWORDS):
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        val_str = node.value.value
                        if len(val_str) > 4 and not val_str.startswith("env_"):
                            self.findings.append({
                                "rule_id": "SEC-HARDCODED-SECRET",
                                "analyzer": "PythonAST",
                                "category": "Security",
                                "severity": "HIGH",
                                "line": node.lineno,
                                "message": f"Potential hardcoded secret or API key assigned to variable '{target.id}'.",
                                "snippet": f"{target.id} = '***'"
                            })
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        func_name = ""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr

        # Dangerous functions
        if func_name in ("eval", "exec"):
            self.findings.append({
                "rule_id": "SEC-DANGEROUS-EVAL",
                "analyzer": "PythonAST",
                "category": "Security",
                "severity": "CRITICAL",
                "line": node.lineno,
                "message": f"Dangerous dynamic execution via '{func_name}()'.",
                "snippet": self._get_line_snippet(node.lineno)
            })
        elif func_name == "system" and isinstance(node.func, ast.Attribute):
            self.findings.append({
                "rule_id": "SEC-COMMAND-INJECTION",
                "analyzer": "PythonAST",
                "category": "Security",
                "severity": "HIGH",
                "line": node.lineno,
                "message": "Direct OS command execution via 'os.system()'. Consider subprocess with list arguments.",
                "snippet": self._get_line_snippet(node.lineno)
            })
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        # Detect bare except or empty pass
        if node.type is None:
            self.findings.append({
                "rule_id": "PY-BARE-EXCEPT",
                "analyzer": "PythonAST",
                "category": "Reliability",
                "severity": "LOW",
                "line": node.lineno,
                "message": "Bare 'except:' catches all exceptions, including SystemExit and KeyboardInterrupt.",
                "snippet": self._get_line_snippet(node.lineno)
            })
        if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
            self.findings.append({
                "rule_id": "PY-SILENT-EXCEPTION",
                "analyzer": "PythonAST",
                "category": "Reliability",
                "severity": "MEDIUM",
                "line": node.lineno,
                "message": "Silenced exception with 'pass'. Errors should be logged or handled.",
                "snippet": self._get_line_snippet(node.lineno)
            })
        self.generic_visit(node)
