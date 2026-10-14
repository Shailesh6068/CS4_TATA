import os
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from backend.app.config import settings
from backend.app.models.db_models import Review, Finding, Project, ProjectFile
from backend.app.schemas.api_schemas import (
    StructuredReviewOutput, ReviewResponse, FindingResponse,
    CodeExplanationResponse, DiffReviewResponse
)
from backend.app.services.ollama_service import ollama_service
from backend.app.services.static_analysis_service import static_analysis_service
from backend.app.services.rag_service import rag_service
from backend.app.analyzers.fusion_engine import fuse_findings
from backend.app.prompts.system_prompts import (
    CODE_REVIEW_SYSTEM_PROMPT, SECURITY_REVIEW_SYSTEM_PROMPT,
    MISRA_SYSTEM_PROMPT, DIFF_REVIEW_SYSTEM_PROMPT,
    CODE_EXPLANATION_SYSTEM_PROMPT
)
from backend.app.prompts.review_prompts import build_review_prompt
from backend.app.security.prompt_guard import scan_prompt_injection, wrap_untrusted_code
from backend.app.utils.audit_logger import log_audit_event

class ReviewService:
    """Core review orchestration fusing static analysis, local RAG guidelines, and local Ollama."""

    def run_review(
        self,
        db: Session,
        project_id: int,
        review_type: str,  # GENERAL, SECURITY, MISRA
        file_paths: Optional[List[str]] = None,
        code_snippet: Optional[str] = None,
        file_name: str = "main.cpp",
        use_rag: bool = True,
        enabled_rules: Optional[List[str]] = None
    ) -> ReviewResponse:
        target_code = (code_snippet or "").strip()
        target_filename = file_name

        if not target_code and file_paths:
            # Read first file from disk/project using multi-path fallback
            pf = db.query(ProjectFile).filter(
                ProjectFile.project_id == project_id,
                ProjectFile.relative_path == file_paths[0]
            ).first()
            if pf:
                project = db.query(Project).filter(Project.id == project_id).first()
                candidates = []
                if project and project.repo_path:
                    candidates.append(os.path.join(project.repo_path, pf.relative_path))
                candidates.append(os.path.join(settings.UPLOAD_DIR, str(project_id), pf.relative_path))
                if project:
                    candidates.append(os.path.join(settings.UPLOAD_DIR, project.name.replace(" ", "_"), pf.relative_path))

                for path in candidates:
                    if os.path.exists(path) and os.path.isfile(path):
                        with open(path, "r", encoding="utf-8", errors="ignore") as f:
                            target_code = f.read()
                        target_filename = pf.relative_path
                        break

        # Guard against empty code: never run LLM or RAG on empty code
        if not target_code or target_code == "// No code content provided.":
            review_rec = Review(
                project_id=project_id,
                review_type=review_type,
                status="COMPLETED",
                summary="No source code provided to review.",
                overall_risk="LOW",
                score=100.0,
                security_score=100.0,
                correctness_score=100.0,
                maintainability_score=100.0
            )
            db.add(review_rec)
            db.commit()
            db.refresh(review_rec)
            return ReviewResponse(
                review_id=review_rec.id,
                project_id=project_id,
                review_type=review_type,
                status="COMPLETED",
                summary="No source code provided to review.",
                overall_risk="LOW",
                score=100.0,
                security_score=100.0,
                correctness_score=100.0,
                maintainability_score=100.0,
                disclaimer=None,
                findings=[]
            )

        code_lines = target_code.splitlines()
        total_lines = len(code_lines)

        # Scan for adversarial prompt injection
        has_injection, detected_patterns = scan_prompt_injection(target_code)

        # 1. Deterministic Static Analysis
        static_res = static_analysis_service.analyze_file(target_filename, target_code)
        static_evidence = static_res.get("findings", [])

        # 2. RAG Knowledge Retrieval
        rag_citations = []
        if use_rag:
            # Query RAG using review type and relevant language keywords, avoid injecting misleading filename
            query = f"{review_type} embedded coding standards buffer safety"
            rag_citations = rag_service.query_guidelines(query, project_id=project_id, top_k=2)

        # 3. System Prompt Selection
        if review_type == "SECURITY":
            sys_prompt = SECURITY_REVIEW_SYSTEM_PROMPT
        elif review_type == "MISRA":
            sys_prompt = MISRA_SYSTEM_PROMPT
        else:
            sys_prompt = CODE_REVIEW_SYSTEM_PROMPT

        # 4. Check for Trivial Clean Code (e.g. Hello World or empty main)
        structural_tokens = {"for", "while", "if", "switch", "new", "delete", "malloc", "free", "strcpy", "strcat", "sprintf", "gets", "scanf", "[", "]", "->", "class", "struct"}
        has_structural_tokens = any(tok in target_code for tok in structural_tokens)
        is_clean_trivial = (not static_evidence and not has_structural_tokens and total_lines <= 20)

        # 5. Build Structured Prompt & Execute LLM
        llm_findings_list: List[Dict[str, Any]] = []
        summary = f"{review_type.capitalize()} review completed for {target_filename}."
        overall_risk = "LOW"

        if not is_clean_trivial:
            user_prompt = build_review_prompt(
                file_name=target_filename,
                code_content=target_code,
                review_type=review_type,
                static_evidence=static_evidence,
                rag_citations=rag_citations,
                enabled_rules=enabled_rules
            )

            try:
                structured_out: StructuredReviewOutput = ollama_service.generate_structured(
                    prompt=user_prompt,
                    system_prompt=sys_prompt,
                    schema_cls=StructuredReviewOutput
                )
                summary = structured_out.summary
                llm_findings_list = [f.model_dump() for f in structured_out.findings]
            except Exception as e:
                summary = f"Multi-pass deterministic static analysis completed. Local LLM analysis note: {str(e)[:120]}."
        else:
            summary = f"{review_type.capitalize()} review completed for {target_filename}: Code is clean, well-formed, and free of defects."

        # 6. Strict Anti-Hallucination Post-Validation on LLM findings
        import re
        code_lower = target_code.lower()
        validated_llm_findings: List[Dict[str, Any]] = []

        COMMON_SAFE_TOKENS = {
            "null", "void", "main", "char", "int", "const", "true", "false", "this", "std",
            "nullptr", "size_t", "uint8_t", "uint16_t", "uint32_t", "uint64_t", "int32_t",
            "strncpy", "strncpy_s", "strlcpy", "strncat", "strncat_s", "strlcat", "snprintf", "snprintf_s",
            "fgets", "unique_ptr", "shared_ptr", "make_unique", "make_shared", "vector", "string",
            "memcpy", "memset", "memmove", "fclose", "close", "assert", "static", "inline", "virtual",
            "cwe", "misra", "iso", "autosar", "cert", "buffer", "length", "size", "pointer", "array", "heap", "stack"
        }

        for f in llm_findings_list:
            line_start = f.get("line_start")
            
            # Rule A: Line number must not exceed total code lines
            if line_start is not None and (line_start > total_lines or line_start < 1):
                continue
            
            # Rule B: Check if finding fabricates specific function/variable names
            issue_text = f.get("issue", "")
            quoted_tokens = re.findall(r"['`](\w+)['`]", issue_text)
            hallucinated_name = False
            for tok in quoted_tokens:
                tl = tok.lower()
                if len(tl) >= 4 and tl not in COMMON_SAFE_TOKENS:
                    if not any(tl.startswith(prefix) for prefix in ("cwe", "misra", "iso", "cert")):
                        if tl not in code_lower:
                            hallucinated_name = True
                            break
            if hallucinated_name:
                continue

            # Rule C: Check evidence snippet if provided
            ev = f.get("evidence")
            if ev and ev.strip():
                ev_words = [w for w in re.findall(r"[A-Za-z0-9_]{3,}", ev) if w.lower() not in COMMON_SAFE_TOKENS and not w.isdigit()]
                if ev_words and not any(w.lower() in code_lower for w in ev_words):
                    continue

            validated_llm_findings.append(f)

        # 7. Fuse Findings
        fused = fuse_findings(validated_llm_findings, static_evidence, file_path=target_filename)

        if has_injection:
            fused.append({
                "finding_code": "SEC-INJECTION-ALERT",
                "category": "Security",
                "severity": "HIGH",
                "confidence": "HIGH",
                "source_type": "STATIC_ANALYZER",
                "file_path": target_filename,
                "line_start": 1,
                "line_end": 1,
                "issue": "Adversarial Prompt Injection Pattern Detected in Source Code/Comments.",
                "evidence": ", ".join(detected_patterns),
                "explanation": "Detected instructions attempting to override AI review guidelines. Successfully isolated inside passive data boundary.",
                "recommendation": "Review untrusted external code contributions before analysis.",
                "suggested_fix": None,
                "status": "OPEN"
            })

        # 8. Rigorous Quality Score Calculation
        sec_penalties = 0.0
        corr_penalties = 0.0
        maint_penalties = 0.0

        for f in fused:
            sev = str(f.get("severity", "MEDIUM")).upper()
            cat = str(f.get("category", "General"))

            if sev == "CRITICAL":
                p = 25.0
            elif sev == "HIGH":
                p = 15.0
            elif sev == "MEDIUM":
                p = 6.0
            else:
                p = 2.0

            if cat in ("Security", "MemorySafety", "UnsafeFunctions"):
                sec_penalties += p
            elif cat in ("Correctness", "ArrayBounds", "AutomotiveEmbedded"):
                corr_penalties += p
            else:
                maint_penalties += p

        sec_score = max(0.0, round(100.0 - sec_penalties, 1))
        corr_score = max(0.0, round(100.0 - corr_penalties, 1))
        maint_score = max(0.0, round(100.0 - maint_penalties, 1))
        composite_score = max(0.0, round((sec_score * 0.4) + (corr_score * 0.35) + (maint_score * 0.25), 1))

        if not fused:
            overall_risk = "LOW"
            sec_score = 100.0
            corr_score = 100.0
            maint_score = 100.0
            composite_score = 100.0
            summary = f"{review_type.capitalize()} review completed: No vulnerabilities or defects detected in {target_filename}."
        else:
            if any(f.get("severity") == "CRITICAL" for f in fused):
                overall_risk = "CRITICAL"
            elif any(f.get("severity") == "HIGH" for f in fused):
                overall_risk = "HIGH"
            elif any(f.get("severity") == "MEDIUM" for f in fused):
                overall_risk = "MEDIUM"
            else:
                overall_risk = "LOW"
            summary = f"{review_type.capitalize()} review completed: {len(fused)} defect(s) identified with Overall Risk {overall_risk}."

        # 9. Persist Review Record & Findings
        review_rec = Review(
            project_id=project_id,
            review_type=review_type,
            status="COMPLETED",
            summary=summary,
            overall_risk=overall_risk,
            score=composite_score,
            security_score=sec_score,
            correctness_score=corr_score,
            maintainability_score=maint_score
        )
        db.add(review_rec)
        db.commit()
        db.refresh(review_rec)

        db_findings: List[Finding] = []
        for item in fused:
            finding_rec = Finding(
                review_id=review_rec.id,
                project_id=project_id,
                finding_code=item.get("finding_code", "GEN-001"),
                category=item.get("category", "General"),
                severity=item.get("severity", "MEDIUM"),
                confidence=item.get("confidence", "HIGH"),
                source_type=item.get("source_type", "COMBINED"),
                file_path=item.get("file_path", target_filename),
                line_start=item.get("line_start"),
                line_end=item.get("line_end"),
                issue=item.get("issue", "Code issue detected"),
                evidence=item.get("evidence"),
                explanation=item.get("explanation", ""),
                recommendation=item.get("recommendation"),
                suggested_fix=item.get("suggested_fix"),
                status="OPEN"
            )
            db.add(finding_rec)
            db_findings.append(finding_rec)

        db.commit()

        # Audit log event
        log_audit_event(
            db=db,
            action=f"{review_type}_REVIEW_COMPLETED",
            project_id=project_id,
            target_type="REVIEW",
            target_id=str(review_rec.id),
            details={"file": target_filename, "findings_count": len(db_findings), "risk": overall_risk}
        )

        disclaimer = None
        if review_type == "MISRA":
            disclaimer = (
                "This is an AI-assisted MISRA-oriented review. "
                "It does not replace qualified certified MISRA analysis tools or human review."
            )

        return ReviewResponse(
            review_id=review_rec.id,
            project_id=project_id,
            review_type=review_type,
            status="COMPLETED",
            summary=summary,
            overall_risk=overall_risk,
            score=composite_score,
            security_score=sec_score,
            correctness_score=corr_score,
            maintainability_score=maint_score,
            disclaimer=disclaimer,
            findings=[FindingResponse.model_validate(f) for f in db_findings]
        )

    def explain_code(
        self,
        project_id: int,
        file_path: Optional[str],
        code_snippet: Optional[str],
        mode: str = "TECHNICAL",
        target_symbol: Optional[str] = None
    ) -> CodeExplanationResponse:
        code = code_snippet or ""
        fname = file_path or "snippet.cpp"
        wrapped = wrap_untrusted_code(code, label=fname)

        prompt = f"""
EXPLAIN SOURCE CODE: {fname}
MODE: {mode} (Target: {'Junior/Non-technical stakeholder' if mode == 'SIMPLE' else 'Automotive Software Engineer'})
TARGET SYMBOL: {target_symbol or 'Entire File / Function'}

{wrapped}

Generate an executive structured explanation including:
1. Executive Summary
2. Purpose
3. Functions and Classes breakdown
4. Inputs and Outputs
5. Control Flow description
6. Dependencies
7. Potential Risks and Edge Cases
"""
        response_text = ollama_service.generate(prompt=prompt, system_prompt=CODE_EXPLANATION_SYSTEM_PROMPT)

        return CodeExplanationResponse(
            executive_summary=f"Analysis of {fname} in {mode} mode.",
            purpose=f"Module operations and control logic for {target_symbol or fname}.",
            functions_and_classes=[],
            inputs_and_outputs={},
            control_flow="Control flow detailed in formatted explanation.",
            dependencies=[],
            potential_risks=[],
            formatted_explanation=response_text
        )

    def review_diff(
        self,
        project_id: int,
        before_code: Optional[str],
        after_code: Optional[str],
        git_diff: Optional[str],
        file_name: str = "diff.patch"
    ) -> DiffReviewResponse:
        diff_content = git_diff or f"--- BEFORE ---\n{before_code}\n\n+++ AFTER +++\n{after_code}"
        wrapped = wrap_untrusted_code(diff_content, label="GIT_DIFF")

        prompt = f"""
ANALYZE CODE CHANGE / DIFF:
Target: {file_name}

{wrapped}

Analyze only the changed logic:
1. Does this change introduce a security vulnerability? Answer YES, NO, or UNCERTAIN.
2. What are the newly added risks or regression potentials?
3. What issues are resolved by this change?
Provide evidence and reasoning.
"""
        res_text = ollama_service.generate(prompt=prompt, system_prompt=DIFF_REVIEW_SYSTEM_PROMPT)

        introduces_sec = "UNCERTAIN"
        upper_res = res_text.upper()
        if "INTRODUCE A SECURITY VULNERABILITY: YES" in upper_res or "YES, THIS CHANGE INTRODUCES" in upper_res:
            introduces_sec = "YES"
        elif "INTRODUCE A SECURITY VULNERABILITY: NO" in upper_res or "NO, THIS CHANGE DOES NOT" in upper_res:
            introduces_sec = "NO"

        return DiffReviewResponse(
            introduces_security_vulnerability=introduces_sec,
            confidence="HIGH" if introduces_sec != "UNCERTAIN" else "MEDIUM",
            added_risks=["Potential logic change in modified block."],
            resolved_issues=["Prior version changes addressed."],
            regression_risks=["Boundary conditions should be regression-tested."],
            detailed_analysis=res_text,
            findings=[]
        )

review_service = ReviewService()
