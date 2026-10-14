from typing import List, Optional
from backend.app.security.prompt_guard import wrap_untrusted_code, wrap_rag_guidelines

def build_review_prompt(
    file_name: str,
    code_content: str,
    review_type: str,
    static_evidence: Optional[List[dict]] = None,
    rag_citations: Optional[List[dict]] = None,
    enabled_rules: Optional[List[str]] = None
) -> str:
    """
    Constructs a grounded, prompt-injection protected review prompt
    combining source code, deterministic analyzer output, and internal guidelines.
    """
    lines = code_content.splitlines()
    total_lines = len(lines)
    numbered_lines = [f"{i:3d} | {l}" for i, l in enumerate(lines, start=1)]
    numbered_code_block = "\n".join(numbered_lines)

    wrapped_code = wrap_untrusted_code(code_content, label=file_name)
    
    sections = [
        f"TARGET FILE: {file_name}",
        f"REVIEW TYPE: {review_type.upper()}",
        f"TOTAL CODE LINES: {total_lines}",
        "",
        "--- SOURCE CODE (LINE NUMBERED) ---",
        numbered_code_block,
        "",
        "--- RAW UNTRUSTED CODE PAYLOAD ---",
        wrapped_code,
    ]

    # Incorporate Enabled Compliance Rules
    if enabled_rules:
        sections.append("\n--- ENABLED COMPLIANCE RULES ---")
        sections.append("Evaluate compliance specifically against the following active rules:")
        for r in enabled_rules:
            sections.append(f"- {r}")

    # Incorporate Deterministic Static Analysis Findings as Evidence
    if static_evidence:
        sections.append("\n--- MULTI-PASS DETERMINISTIC STATIC ANALYSIS EVIDENCE ---")
        sections.append("The deterministic analyzers have pre-scanned the code and identified the following candidate defects:")
        for idx, item in enumerate(static_evidence, start=1):
            sections.append(
                f"{idx}. [{item.get('analyzer', 'STATIC')}] [{item.get('category', 'General')}] "
                f"Rule: {item.get('rule_id', 'N/A')} Line: {item.get('line', '?')} Severity: {item.get('severity', 'MEDIUM')}\n"
                f"   Message: {item.get('message', '')}\n"
                f"   Snippet: {item.get('snippet', '')}\n"
                f"   Root Cause: {item.get('root_cause', 'N/A')}\n"
                f"   Standards: {item.get('standards', 'N/A')}"
            )
        sections.append("Fuse these deterministic findings with your source code analysis. If multiple rules describe the same underlying defect on the same line, combine them into one finding listing all applicable standards.")

    # Incorporate RAG Knowledge Citations
    if rag_citations:
        sections.append("\n--- RETRIEVED APPROVED ENGINEERING STANDARDS (RAG) ---")
        for idx, cit in enumerate(rag_citations, start=1):
            title = cit.get("title", "Standard Document")
            section_name = cit.get("section", "General")
            text = cit.get("content", "")
            wrapped_rag = wrap_rag_guidelines(text, source_info=f"{title} | {section_name}")
            sections.append(wrapped_rag)

    sections.append(f"""
OUTPUT INSTRUCTIONS:
CRITICAL ZERO-DEFECT RULE:
If the source code is valid, correct, and free of defects (e.g. standard Hello World, basic calculations, clean functions), you MUST output:
- "findings": []
- "overall_risk": "LOW"
- "security_score": 100.0
- "correctness_score": 100.0
- "maintainability_score": 100.0
- "summary": "No vulnerabilities or coding standard violations identified in the analyzed code snippet."
DO NOT FABRICATE OR HALLUCINATE ANY FINDING.

STRICT GROUNDING & MULTI-LAYERED COVERAGE:
1. Review the ACTUAL source code line-by-line across all 9 critical areas:
   - Memory Safety (buffer overflows, UAF, double free, leaks, strlen allocation mistakes, mismatched delete)
   - Array & Boundary Safety (out-of-bounds, off-by-one loops '<=' instead of '<', invalid indices)
   - Resource Management (new/delete pairs, file/socket leaks without close, raw pointer ownership)
   - Unsafe Functions (strcpy, strcat, sprintf, gets, unbounded scanf, sizeof(pointer) bugs)
   - Correctness (logic errors, assignment in condition 'if (x = y)', unreachable code, unsigned < 0)
   - Security (CWE vulnerabilities, command injection, format string bugs, hardcoded secrets)
   - Automotive / Embedded C/C++ (MISRA C:2012, MISRA C++:2008/2023, ISO 26262 Part 6, CAN DLC bounds)
   - Performance (strlen in loop conditions, expensive repeated allocations)
   - Maintainability / Code Smells (empty catch blocks, assert side effects)
2. Every "line_start" MUST be an integer between 1 and {total_lines} referencing the exact line in the code block.
3. Every "evidence" must be a verbatim line or expression present in the code.
4. "explanation" MUST include Root Cause, Impact, and Applicable Standards.

Output JSON object with:
- "summary": comprehensive executive engineering summary of all findings
- "overall_risk": "CRITICAL", "HIGH", "MEDIUM", or "LOW"
- "security_score": score 0-100 reflecting memory safety and vulnerability absence
- "correctness_score": score 0-100 reflecting logic correctness, loop bounds, and contract adherence
- "maintainability_score": score 0-100 reflecting resource management, complexity, and standards compliance
- "findings": array of finding objects, each with:
    - "finding_code": unique code (e.g. "MEM-001", "ARR-002", "MISRA-21.6", "CWE-120")
    - "category": "MemorySafety", "ArrayBounds", "ResourceManagement", "UnsafeFunctions", "Correctness", "Security", "AutomotiveEmbedded", "Performance", or "Maintainability"
    - "severity": "CRITICAL", "HIGH", "MEDIUM", or "LOW"
    - "confidence": "HIGH", "MEDIUM", or "LOW"
    - "source_type": "LLM"
    - "file": "{file_name}"
    - "line_start": starting line number (integer between 1 and {total_lines})
    - "line_end": ending line number
    - "issue": concise title of defect
    - "evidence": exact snippet of problematic code
    - "explanation": complete root cause, undefined behavior impact, and applicable standards
    - "recommendation": professional architectural remediation guidance
    - "suggested_fix": exact corrected code replacing the defect
""")
    return "\n".join(sections)

def build_debug_prompt(
    source_code: Optional[str],
    compiler_error: Optional[str],
    runtime_error: Optional[str],
    stack_trace: Optional[str],
    log_content: Optional[str],
    user_description: Optional[str],
    static_evidence: Optional[List[dict]] = None
) -> str:
    """Builds a debug root-cause prompt with error evidence."""
    parts = ["DEBUGGING AND ROOT-CAUSE ANALYSIS REQUEST", ""]
    
    if user_description:
        parts.append(f"USER PROBLEM STATEMENT:\n{user_description}\n")

    if compiler_error:
        parts.append(f"COMPILER ERROR EVIDENCE:\n{compiler_error}\n")

    if runtime_error:
        parts.append(f"RUNTIME ERROR / EXCEPTION:\n{runtime_error}\n")

    if stack_trace:
        parts.append(f"STACK TRACE:\n{stack_trace}\n")

    if log_content:
        parts.append(f"SYSTEM / ECU LOG EVIDENCE:\n{log_content}\n")

    if source_code:
        parts.append(wrap_untrusted_code(source_code, label="AFFECTED_SOURCE_CODE"))

    if static_evidence:
        parts.append("STATIC ANALYSIS EVIDENCE:")
        for ev in static_evidence:
            parts.append(f"- Line {ev.get('line')}: {ev.get('message')}")

    parts.append("""
OUTPUT INSTRUCTIONS:
Respond in JSON conforming to:
{
  "error_summary": "Short description of the fault",
  "severity": "CRITICAL" | "HIGH" | "MEDIUM" | "LOW",
  "likely_root_cause": "Detailed technical root cause",
  "evidence": "Exact lines or tokens confirming this cause",
  "affected_file": "File name or null",
  "affected_line": Line number integer or null,
  "explanation": "Why the bug or compilation error happens",
  "suggested_fix": "Clear step-by-step fix",
  "corrected_code": "Full corrected code block or snippet",
  "confidence": "HIGH" | "MEDIUM" | "LOW",
  "limitations": "Assumptions or constraints"
}
""")
    return "\n".join(parts)
