import re
from typing import List, Dict, Any

# GCC / Clang format: path/to/file.cpp:42:10: error: 'x' was not declared in this scope
GCC_CLANG_RE = re.compile(
    r'^(?P<file>[a-zA-Z0-9_\-\./\\]+\.[a-zA-Z0-9]+):(?P<line>\d+):(?P<col>\d+):\s*(?P<type>error|warning|fatal error|note):\s*(?P<msg>.+)$',
    re.IGNORECASE
)

# MSVC format: path\to\file.cpp(42,10): error C2065: 'x': undeclared identifier
MSVC_RE = re.compile(
    r'^(?P<file>[a-zA-Z0-9_\-\./\\]+\.[a-zA-Z0-9]+)\((?P<line>\d+)(?:,\s*(?P<col>\d+))?\):\s*(?P<type>error|warning|fatal error)\s*(?P<code>[A-Z0-9]+)?:\s*(?P<msg>.+)$',
    re.IGNORECASE
)

def parse_compiler_log(log_content: str) -> Dict[str, Any]:
    lines = log_content.splitlines()
    entries: List[Dict[str, Any]] = []
    error_count = 0
    warning_count = 0

    for raw_line in lines:
        line_clean = raw_line.strip()
        m = GCC_CLANG_RE.match(line_clean)
        if m:
            entry_type = m.group("type").lower()
            if "error" in entry_type:
                error_count += 1
            elif "warning" in entry_type:
                warning_count += 1
                
            entries.append({
                "compiler": "GCC/Clang",
                "file": m.group("file"),
                "line": int(m.group("line")),
                "column": int(m.group("col")),
                "severity": "ERROR" if "error" in entry_type else "WARNING",
                "raw_type": m.group("type"),
                "code": None,
                "message": m.group("msg").strip()
            })
            continue

        m_msvc = MSVC_RE.match(line_clean)
        if m_msvc:
            entry_type = m_msvc.group("type").lower()
            if "error" in entry_type:
                error_count += 1
            elif "warning" in entry_type:
                warning_count += 1

            col_val = int(m_msvc.group("col")) if m_msvc.group("col") else 1
            entries.append({
                "compiler": "MSVC",
                "file": m_msvc.group("file"),
                "line": int(m_msvc.group("line")),
                "column": col_val,
                "severity": "ERROR" if "error" in entry_type else "WARNING",
                "raw_type": m_msvc.group("type"),
                "code": m_msvc.group("code"),
                "message": m_msvc.group("msg").strip()
            })

    # Categorize errors
    categories: Dict[str, int] = {}
    for entry in entries:
        msg = entry["message"].lower()
        cat = "General"
        if "undeclared" in msg or "not declared" in msg or "cannot find" in msg:
            cat = "Undefined Symbol"
        elif "type" in msg or "conversion" in msg or "cannot convert" in msg:
            cat = "Type Mismatch"
        elif "syntax" in msg or "expected" in msg:
            cat = "Syntax Error"
        elif "link" in msg or "unresolved external" in msg:
            cat = "Linker Error"
        elif "deprecated" in msg:
            cat = "Deprecation"
        elif "overflow" in msg or "memory" in msg or "bounds" in msg:
            cat = "Memory / Buffer"
        
        entry["category"] = cat
        categories[cat] = categories.get(cat, 0) + 1

    return {
        "total_errors": error_count,
        "total_warnings": warning_count,
        "entries": entries,
        "category_distribution": categories
    }
