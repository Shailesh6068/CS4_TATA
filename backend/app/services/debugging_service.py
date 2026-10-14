import re
from typing import Dict, Any, List, Optional
from backend.app.schemas.api_schemas import (
    DebugAnalyzeRequest, DebugAnalyzeResponse,
    LogAnalysisRequest, LogAnalysisResponse
)
from backend.app.services.ollama_service import ollama_service
from backend.app.analyzers.compiler_log_analyzer import parse_compiler_log
from backend.app.prompts.system_prompts import DEBUG_SYSTEM_PROMPT, LOG_ANALYSIS_SYSTEM_PROMPT
from backend.app.prompts.review_prompts import build_debug_prompt
from backend.app.security.prompt_guard import wrap_untrusted_code

class DebuggingService:
    """Debugging assistant for compiler errors, runtime crashes, and ECU logs."""

    def analyze_debug(self, req: DebugAnalyzeRequest) -> DebugAnalyzeResponse:
        # Check if code is clean and no error symptoms were provided
        has_error_evidence = bool(
            (req.compiler_error and req.compiler_error.strip()) or
            (req.runtime_error and req.runtime_error.strip()) or
            (req.stack_trace and req.stack_trace.strip()) or
            (req.log_content and req.log_content.strip()) or
            (req.user_description and req.user_description.strip())
        )

        from backend.app.services.static_analysis_service import static_analysis_service
        static_check = static_analysis_service.analyze_file(req.file_path or "snippet.cpp", req.source_code or "")
        static_findings = static_check.get("findings", [])

        if not has_error_evidence and not static_findings and req.source_code:
            return DebugAnalyzeResponse(
                error_summary="No Errors or Bugs Detected",
                severity="LOW",
                likely_root_cause="The provided source code is syntactically valid and clean. No compiler error, stack trace, or bug description was provided.",
                evidence="Syntax and structure appear valid.",
                affected_file=req.file_path or "source",
                affected_line=None,
                explanation="No syntax violations, buffer issues, or compiler diagnostics were detected in this code snippet.",
                suggested_fix="No fix needed. The code is already correct and functional.",
                corrected_code=req.source_code,
                confidence="HIGH",
                limitations="Analyzed without build log or runtime execution trace. If an error occurs during build/runtime, please paste the compiler output or error message."
            )

        compiler_info = None
        if req.compiler_error:
            compiler_info = parse_compiler_log(req.compiler_error)

        static_ev = []
        if compiler_info and compiler_info.get("entries"):
            for e in compiler_info["entries"][:5]:
                static_ev.append({
                    "line": e.get("line"),
                    "message": f"[{e.get('compiler')}] {e.get('severity')}: {e.get('message')}"
                })

        user_prompt = build_debug_prompt(
            source_code=req.source_code,
            compiler_error=req.compiler_error,
            runtime_error=req.runtime_error,
            stack_trace=req.stack_trace,
            log_content=req.log_content,
            user_description=req.user_description,
            static_evidence=static_ev
        )

        try:
            resp: DebugAnalyzeResponse = ollama_service.generate_structured(
                prompt=user_prompt,
                system_prompt=DEBUG_SYSTEM_PROMPT,
                schema_cls=DebugAnalyzeResponse
            )
            return resp
        except Exception as e:
            # Deterministic fallback extraction
            first_err = compiler_info["entries"][0] if compiler_info and compiler_info.get("entries") else {}
            return DebugAnalyzeResponse(
                error_summary=first_err.get("message", "Compilation or runtime failure detected."),
                severity="HIGH" if first_err.get("severity") == "ERROR" else "MEDIUM",
                likely_root_cause=f"Diagnostic error reported by compiler/runtime: {first_err.get('message', 'Unspecified error')}.",
                evidence=f"{first_err.get('file', 'source')}:{first_err.get('line', '?')}",
                affected_file=first_err.get("file"),
                affected_line=first_err.get("line"),
                explanation=f"Compiler diagnostic identified syntax or type conflict. LLM assistant output fallback: {str(e)[:120]}.",
                suggested_fix="Verify symbol declarations, include headers, and type compatibility.",
                corrected_code=None,
                confidence="HIGH" if first_err else "LOW",
                limitations="Analysis derived from deterministic compiler diagnostic stream."
            )

    def analyze_logs(self, req: LogAnalysisRequest) -> LogAnalysisResponse:
        lines = req.log_content.splitlines()
        timeline: List[Dict[str, Any]] = []
        repeated_errors: Dict[str, int] = {}

        # Heuristic timestamp regex: [2026-10-07 10:14:22] or 12:34:56.789
        ts_re = re.compile(r'(?:\[(?P<ts1>[^\]]+)\]|(?P<ts2>\d{2}:\d{2}:\d{2}(?:\.\d+)?))\s*(?:\[(?P<lvl>[A-Z]+)\]|(?P<lvl2>ERROR|WARN|INFO|CRITICAL|FATAL))?\s*(?P<msg>.+)', re.IGNORECASE)

        for line in lines:
            m = ts_re.match(line.strip())
            if m:
                ts = m.group("ts1") or m.group("ts2") or "00:00:00"
                lvl = (m.group("lvl") or m.group("lvl2") or "INFO").upper()
                msg = m.group("msg")

                timeline.append({
                    "timestamp": ts,
                    "level": lvl,
                    "message": msg
                })

                if lvl in ("ERROR", "CRITICAL", "FATAL", "WARN"):
                    repeated_errors[msg] = repeated_errors.get(msg, 0) + 1

        repeated_list = [{"error": k, "count": v} for k, v in sorted(repeated_errors.items(), key=lambda x: x[1], reverse=True)[:5]]

        # LLM summary
        wrapped = wrap_untrusted_code(req.log_content[:3000], label="LOG_EXTRACT")
        prompt = f"""
ANALYZE AUTOMOTIVE ECU / SYSTEM LOG:
Type: {req.log_type}

{wrapped}

Extract failure sequence, identify root cause, and specify recommended automotive software actions.
Return a response including:
1. Root Cause Summary
2. Suspected Source Code or Modules (if any mentioned or implied)
3. Actionable Recommendations (as numbered or bulleted items)
"""
        llm_text = ""
        try:
            llm_text = ollama_service.generate(prompt=prompt, system_prompt=LOG_ANALYSIS_SYSTEM_PROMPT)
        except Exception:
            llm_text = f"Automated log parser processed {len(timeline)} events. Repeated faults found: {len(repeated_list)}."

        # Extract recommendations from LLM text bullets/numbered lines
        extracted_recs = []
        if llm_text:
            raw_bullets = re.findall(r'(?:^|\n)\s*(?:[-*•]|\d+\.)\s+(.+)', llm_text)
            extracted_recs = [b.strip() for b in raw_bullets if len(b.strip()) > 10][:5]

        if not extracted_recs:
            if req.log_type == "ECU":
                extracted_recs = [
                    "Inspect communication busload and message timeout parameters.",
                    "Verify sensor acquisition retry count before entering fail-safe mode.",
                    "Review diagnostic trouble code (DTC) clearing routines."
                ]
            else:
                extracted_recs = [
                    "Inspect system runtime error handling and exception hooks.",
                    "Verify memory bounds and resource allocation in suspect functions.",
                    "Examine recent commits affecting the failing execution path."
                ]

        # Extract any mentioned source file names (.cpp, .c, .h, .py, etc.)
        detected_files = list(set(re.findall(r'\b[A-Za-z0-9_/-]+\.(?:cpp|c|h|hpp|py|cc|cxx)\b', req.log_content + " " + llm_text)))
        related_src = " / ".join(detected_files[:3]) if detected_files else None

        return LogAnalysisResponse(
            timeline=timeline[:50],
            error_summary=f"Processed {len(timeline)} log records with {sum(repeated_errors.values())} warnings/faults.",
            repeated_errors=repeated_list,
            possible_root_cause=llm_text[:600] if llm_text else "Repeated sensor timeout or communication error.",
            related_source_code=related_src,
            recommendations=extracted_recs
        )

debugging_service = DebuggingService()
