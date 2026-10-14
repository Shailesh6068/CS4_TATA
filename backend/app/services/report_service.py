import os
import json
import csv
from io import StringIO
from datetime import datetime, UTC
from typing import List, Dict, Any
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from backend.app.config import settings

class ReportService:
    """Generates professional engineering reports in PDF, JSON, CSV, and Markdown formats."""

    def generate_markdown_report(self, report_data: Dict[str, Any]) -> str:
        p_name = report_data.get("project_name", "Automotive Project")
        date_str = report_data.get("date", datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"))
        summary = report_data.get("summary", "Automated code review completed.")
        overall_risk = report_data.get("overall_risk", "MEDIUM")
        findings = report_data.get("findings", [])

        md = [
            f"# Engineering Code Review Report: {p_name}",
            f"**Review Date:** {date_str}  ",
            f"**Overall Risk:** {overall_risk}  ",
            f"**Files Analyzed:** {report_data.get('files_analyzed', 0)}  ",
            f"**Lines of Code Analyzed:** {report_data.get('lines_analyzed', 0)}  ",
            "",
            "## 1. Executive Summary",
            summary,
            "",
            "## 2. Risk & Quality Metrics",
            f"- **Overall Risk Level:** {overall_risk}",
            f"- **Security Score:** {report_data.get('security_score', 85.0)}/100",
            f"- **Correctness Score:** {report_data.get('correctness_score', 80.0)}/100",
            f"- **Maintainability Score:** {report_data.get('maintainability_score', 82.0)}/100",
            "",
            "## 3. Findings Summary",
            f"Total findings identified: {len(findings)}",
            "",
            "| ID | Category | Severity | File | Line | Source | Issue |",
            "|---|---|---|---|---|---|---|"
        ]

        for f in findings:
            line_val = f.get('line_start') or '-'
            md.append(f"| {f.get('finding_code', 'F-001')} | {f.get('category')} | {f.get('severity')} | {f.get('file_path')} | {line_val} | {f.get('source_type')} | {f.get('issue')} |")

        md.extend([
            "",
            "## 4. Detailed Findings & Recommendations",
        ])

        for f in findings:
            md.append(f"### Finding {f.get('finding_code')}: {f.get('issue')}")
            md.append(f"- **Severity:** {f.get('severity')} | **Confidence:** {f.get('confidence')} | **Source:** {f.get('source_type')}")
            md.append(f"- **Location:** `{f.get('file_path')}` (Line {f.get('line_start') or 'N/A'})")
            if f.get('evidence'):
                md.append(f"- **Evidence:** `{f.get('evidence')}`")
            md.append(f"- **Explanation:** {f.get('explanation')}")
            if f.get('recommendation'):
                md.append(f"- **Recommendation:** {f.get('recommendation')}")
            if f.get('suggested_fix'):
                md.append(f"```cpp\n// Suggested remediation:\n{f.get('suggested_fix')}\n```")
            md.append("")

        md.extend([
            "## 5. Engineering Recommendations",
            "- Validate all dynamic memory and pointer casts against MISRA C:2012 guidelines.",
            "- Enforce input buffer bounds checks prior to memcpy in ECU message unpacking.",
            "- Remove hardcoded diagnostic credentials and replace with secure HSM / key stores.",
            "",
            "## 6. Human Review & Verification Status",
            "All Critical and High severity findings require manual confirmation and sign-off by a certified automotive safety software engineer.",
            "",
            "## 7. Important Engineering Limitations & Disclaimers",
            "> [!IMPORTANT]",
            "> - AI and static analysis findings may include false positives or false negatives.",
            "> - MISRA-oriented reviews are AI-assisted heuristics and do not constitute official compliance verification.",
            "> - The system must not be used as an autonomous release-approval gate without qualified human review."
        ])

        return "\n".join(md)

    def generate_json_report(self, report_data: Dict[str, Any]) -> str:
        return json.dumps(report_data, indent=2)

    def generate_csv_report(self, report_data: Dict[str, Any]) -> str:
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["Finding Code", "Category", "Severity", "Confidence", "Source Type", "File Path", "Line Start", "Issue", "Status"])
        for f in report_data.get("findings", []):
            writer.writerow([
                f.get("finding_code"),
                f.get("category"),
                f.get("severity"),
                f.get("confidence"),
                f.get("source_type"),
                f.get("file_path"),
                f.get("line_start"),
                f.get("issue"),
                f.get("status", "OPEN")
            ])
        return output.getvalue()

    def generate_pdf_report(self, report_data: Dict[str, Any], output_path: str) -> str:
        """Generates a formal PDF engineering report using ReportLab."""
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#1E293B")
        )
        h2_style = ParagraphStyle(
            "DocH2",
            parent=styles["Heading2"],
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#0F172A")
        )
        body_style = ParagraphStyle(
            "DocBody",
            parent=styles["Normal"],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#334155")
        )

        elements = []

        # Title
        p_name = report_data.get("project_name", "Automotive ECU Controller")
        elements.append(Paragraph(f"SecureCode AI: Engineering Review Report", title_style))
        elements.append(Paragraph(f"Project: <b>{p_name}</b> | Generated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}", body_style))
        elements.append(Spacer(1, 12))

        # Metadata table
        meta_data = [
            ["Overall Risk", report_data.get("overall_risk", "MEDIUM"), "Security Score", f"{report_data.get('security_score', 85)}/100"],
            ["Files Analyzed", str(report_data.get("files_analyzed", 0)), "LOC Analyzed", str(report_data.get("lines_analyzed", 0))],
            ["Total Findings", str(len(report_data.get("findings", []))), "Review Type", report_data.get("review_type", "Comprehensive")]
        ]
        meta_table = Table(meta_data, colWidths=[120, 140, 120, 140])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F1F5F9")),
            ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor("#0F172A")),
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        elements.append(meta_table)
        elements.append(Spacer(1, 14))

        # Executive Summary
        elements.append(Paragraph("1. Executive Summary", h2_style))
        summary_text = report_data.get("summary", "Review completed successfully across codebase.")
        elements.append(Paragraph(summary_text, body_style))
        elements.append(Spacer(1, 12))

        # Findings Table
        elements.append(Paragraph("2. Identified Engineering & Security Findings", h2_style))
        findings = report_data.get("findings", [])
        if findings:
            table_rows = [["ID", "Category", "Sev", "Line", "Issue"]]
            for f in findings[:15]:  # Top findings in PDF summary
                table_rows.append([
                    f.get("finding_code", "F-001"),
                    f.get("category", "General")[:12],
                    f.get("severity", "MED")[:4],
                    str(f.get("line_start") or "-"),
                    Paragraph(f.get("issue", "")[:80], body_style)
                ])
            f_table = Table(table_rows, colWidths=[65, 75, 45, 40, 295])
            f_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1E293B")),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,-1), 8),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('TOPPADDING', (0,0), (-1,-1), 3),
                ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ]))
            elements.append(f_table)
        else:
            elements.append(Paragraph("No severe findings detected in the analyzed scope.", body_style))

        elements.append(Spacer(1, 14))
        elements.append(Paragraph("3. Disclaimer & Verification", h2_style))
        disclaimer = (
            "NOTICE: This AI-assisted report is an engineering advisory tool. It does not replace qualified "
            "MISRA or static-analysis toolchains. Final release approval requires human sign-off."
        )
        elements.append(Paragraph(disclaimer, body_style))

        doc.build(elements)
        return output_path

report_service = ReportService()
