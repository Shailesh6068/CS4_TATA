import re
from typing import List, Dict, Any
from backend.app.schemas.api_schemas import ComplexityMetric, ProjectQualityScoreResponse

class ComplexityService:
    """Calculates code complexity, nesting depths, and automotive quality indicators."""

    def analyze_complexity(self, code_content: str, language: str = "cpp") -> List[ComplexityMetric]:
        lines = code_content.splitlines()
        metrics: List[ComplexityMetric] = []

        # Find functions and analyze their blocks
        if language in ("c", "cpp"):
            func_pattern = re.compile(r'^\s*(?:[\w:*&<>]+\s+)+([A-Za-z_][A-Za-z0-9_:]*)\s*\(([^)]*)\)\s*(?:const)?\s*\{')
        else:
            func_pattern = re.compile(r'^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)\s*:')

        for idx, line in enumerate(lines):
            m = func_pattern.match(line)
            if m:
                func_name = m.group(1)
                params_str = m.group(2)
                param_count = len([p for p in params_str.split(",") if p.strip()]) if params_str.strip() else 0

                # Approximate function length and cyclomatic complexity
                body_lines = 1
                cc = 1
                max_depth = 1
                curr_depth = 0

                for sub_line in lines[idx+1:idx+200]:
                    if "{" in sub_line:
                        curr_depth += sub_line.count("{")
                    if "}" in sub_line:
                        curr_depth = max(0, curr_depth - sub_line.count("}"))
                    max_depth = max(max_depth, curr_depth)
                    
                    # Branches
                    if re.search(r'\b(if|else if|for|while|case|catch)\b', sub_line):
                        cc += 1
                    if "&&" in sub_line or "||" in sub_line:
                        cc += 1

                    body_lines += 1
                    if curr_depth == 0 and body_lines > 1 and "}" in sub_line:
                        break

                risk = "LOW"
                rec = "Function maintains healthy size and low branch branching."
                if cc > 15 or body_lines > 80:
                    risk = "CRITICAL"
                    rec = "Refactor immediately: split into dedicated helper functions to reduce cognitive load and test paths."
                elif cc > 10 or body_lines > 50:
                    risk = "HIGH"
                    rec = "Consider decomposing complex logic into modular subroutines."
                elif cc > 6 or body_lines > 30:
                    risk = "MEDIUM"
                    rec = "Monitor complexity; simplify branching where possible."

                metrics.append(ComplexityMetric(
                    symbol_name=func_name,
                    symbol_type="FUNCTION",
                    cyclomatic_complexity=cc,
                    line_count=body_lines,
                    nested_depth=max_depth,
                    parameter_count=param_count,
                    risk_level=risk,
                    recommendation=rec
                ))

        return metrics

    def compute_quality_score(
        self,
        findings_count: int,
        critical_count: int,
        high_count: int,
        total_loc: int,
        avg_complexity: float
    ) -> ProjectQualityScoreResponse:
        """
        Computes composite engineering quality score (0 - 100).
        Deducts points based on findings density and cyclomatic complexity.
        """
        # Baseline scores
        sec_score = max(30.0, 100.0 - (critical_count * 15.0 + high_count * 6.0))
        corr_score = max(35.0, 100.0 - (critical_count * 10.0 + high_count * 5.0 + (findings_count * 1.5)))
        
        # Maintainability affected by cyclomatic complexity
        maint_penalty = max(0.0, (avg_complexity - 5.0) * 4.0)
        maint_score = max(40.0, 95.0 - maint_penalty - (findings_count * 0.8))
        
        perf_score = max(50.0, 92.0 - (high_count * 3.0))
        read_score = max(45.0, 94.0 - maint_penalty)

        overall = round((sec_score * 0.35) + (corr_score * 0.25) + (maint_score * 0.20) + (perf_score * 0.10) + (read_score * 0.10), 1)

        risk_breakdown = {
            "Overall": "HIGH" if overall < 70 else ("MEDIUM" if overall < 85 else "LOW"),
            "Security": "CRITICAL" if critical_count > 0 else ("HIGH" if high_count > 1 else "LOW"),
            "Maintainability": "HIGH" if avg_complexity > 10 else "LOW",
            "Defect_Risk": "ELEVATED" if findings_count > 5 else "ACCEPTABLE"
        }

        explanation = (
            f"The Overall Code Quality Score ({overall}/100) is a weighted engineering indicator synthesized "
            f"from Security (35%), Correctness (25%), Maintainability (20%), Performance (10%), and Readability (10%). "
            f"Calculated across {total_loc} lines of code with an average cyclomatic complexity of {avg_complexity:.1f}. "
            f"Note: This score is an indicative engineering metric and must be interpreted alongside manual code reviews."
        )

        return ProjectQualityScoreResponse(
            overall_score=overall,
            security_score=round(sec_score, 1),
            correctness_score=round(corr_score, 1),
            maintainability_score=round(maint_score, 1),
            performance_score=round(perf_score, 1),
            readability_score=round(read_score, 1),
            risk_breakdown=risk_breakdown,
            explanation=explanation
        )

complexity_service = ComplexityService()
