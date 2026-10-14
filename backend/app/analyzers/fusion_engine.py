from typing import List, Dict, Any

_SEV_WEIGHT = {
    "CRITICAL": 4,
    "HIGH": 3,
    "MEDIUM": 2,
    "LOW": 1,
    "INFO": 0
}

def _highest_severity(sev1: str, sev2: str) -> str:
    w1 = _SEV_WEIGHT.get(str(sev1).upper(), 1)
    w2 = _SEV_WEIGHT.get(str(sev2).upper(), 1)
    return sev1 if w1 >= w2 else sev2

def fuse_findings(
    llm_findings: List[Dict[str, Any]],
    static_findings: List[Dict[str, Any]],
    file_path: str
) -> List[Dict[str, Any]]:
    """
    Fuses deterministic multi-pass static findings with LLM findings into a single,
    deduplicated, evidence-based findings register.
    
    Rules:
    - If LLM and static tool detect an issue on the same line or token (within 2 lines):
      Merge into a single combined finding, adopting the highest severity, calibrating
      confidence to 'HIGH', and appending standards/CWE references.
    - If multiple static/LLM rules flag the same line for the same underlying root cause,
      combine them into one finding with all applicable standards listed.
    - Unmatched static findings are preserved with complete root-cause and remediation details.
    """
    fused: List[Dict[str, Any]] = []
    matched_static_indices = set()

    # Process each LLM finding
    for llm_f in llm_findings:
        f_copy = dict(llm_f)
        f_copy["file_path"] = f_copy.get("file", file_path)
        llm_line = f_copy.get("line_start")
        
        # Check for static match
        is_matched = False
        if llm_line is not None:
            for idx, stat_f in enumerate(static_findings):
                stat_line = stat_f.get("line")
                if stat_line is not None and abs(stat_line - llm_line) <= 2:
                    is_matched = True
                    matched_static_indices.add(idx)
                    f_copy["source_type"] = "COMBINED"
                    f_copy["confidence"] = "HIGH"
                    # Upgrade severity to the higher of the two
                    f_copy["severity"] = _highest_severity(
                        f_copy.get("severity", "MEDIUM"),
                        stat_f.get("severity", "MEDIUM")
                    )
                    # Enrich snippet / evidence if missing
                    if not f_copy.get("evidence") and stat_f.get("snippet"):
                        f_copy["evidence"] = stat_f.get("snippet")
                    
                    # Merge standards into explanation or recommendation
                    standards = stat_f.get("standards")
                    if standards and standards not in str(f_copy.get("explanation", "")):
                        f_copy["explanation"] = (
                            f"{f_copy.get('explanation', '')}\n[Standards: {standards}]"
                        ).strip()

                    # Adopt suggested fix if LLM didn't provide one
                    if not f_copy.get("suggested_fix") and stat_f.get("suggested_fix"):
                        f_copy["suggested_fix"] = stat_f.get("suggested_fix")

                    # Adopt root cause if available
                    if stat_f.get("root_cause") and "Root Cause:" not in str(f_copy.get("explanation", "")):
                        f_copy["explanation"] = (
                            f"Root Cause: {stat_f.get('root_cause')}\n{f_copy.get('explanation', '')}"
                        ).strip()
                    break

        if not is_matched:
            f_copy["source_type"] = "LLM"
            if f_copy.get("confidence") == "HIGH" and not static_findings:
                f_copy["confidence"] = "MEDIUM"

        fused.append(f_copy)

    # Add unmatched static findings so no deterministic alert is dropped
    for idx, stat_f in enumerate(static_findings):
        if idx not in matched_static_indices:
            rule_id = stat_f.get("rule_id", "STATIC-001")
            line = stat_f.get("line")
            
            # Compose complete explanatory block
            explanation_parts = []
            if stat_f.get("root_cause"):
                explanation_parts.append(f"Root Cause: {stat_f.get('root_cause')}")
            if stat_f.get("impact"):
                explanation_parts.append(f"Impact: {stat_f.get('impact')}")
            if stat_f.get("standards"):
                explanation_parts.append(f"Applicable Standards: {stat_f.get('standards')}")
            if not explanation_parts:
                explanation_parts.append(f"Detected by deterministic analyzer {stat_f.get('analyzer', 'Static')}. Rule: {rule_id}.")
            
            fused.append({
                "finding_code": rule_id,
                "category": stat_f.get("category", "General"),
                "severity": stat_f.get("severity", "MEDIUM"),
                "confidence": "HIGH",
                "source_type": "STATIC_ANALYZER",
                "file_path": file_path,
                "line_start": line,
                "line_end": line,
                "issue": stat_f.get("message", "Deterministic static rule violation"),
                "evidence": stat_f.get("snippet", ""),
                "explanation": "\n".join(explanation_parts),
                "recommendation": stat_f.get("recommendation", "Review and adhere to automotive coding standards for this construct."),
                "suggested_fix": stat_f.get("suggested_fix", None),
                "status": "OPEN"
            })

    # Deduplicate findings on the same line that flag identical rule_id or message
    seen_keys = set()
    deduped: List[Dict[str, Any]] = []
    for f in fused:
        line_ref = f.get("line_start")
        code_ref = f.get("finding_code", "")
        issue_ref = f.get("issue", "")[:40].lower()
        key = (line_ref, code_ref, issue_ref)
        if key not in seen_keys:
            seen_keys.add(key)
            deduped.append(f)

    return deduped
