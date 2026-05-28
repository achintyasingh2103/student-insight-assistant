"""
agents/report_agent.py
Agent 4 — synthesizes all prior outputs into a comprehensive narrative report.
Uses NIM nemotron (highest quality output needed here).
"""

import json
from llm.router import call_llm
from guardrails.output_validator import validate_report
from utils.prompts import REPORT_SYSTEM_PROMPT
from utils.helpers import student_cache_key, truncate_for_prompt


def run(ingestion_result: dict, insight_result: dict, career_result: dict) -> dict:
    """
    Generate the final narrative report from all prior agent outputs.
    Returns validated report dict ready for PDF generation.
    """
    normalized = ingestion_result.get("normalized_data", {})
    student_id = normalized.get("id", "unknown")

    # Compact representations to control token usage
    student_summary = {
        "name": normalized.get("name"),
        "class": normalized.get("class"),
        "section": normalized.get("section"),
        "attendance_percent": normalized.get("attendance_percent"),
        "subjects": normalized.get("subjects", {}),
        "extracurricular": normalized.get("extracurricular", []),
        "teacher_remarks": normalized.get("teacher_remarks", ""),
        "behavioral_observations": normalized.get("behavioral_observations", ""),
        "interests": normalized.get("interests", ""),
        "archetype": normalized.get("archetype", ""),
    }

    insight_summary = {k: v for k, v in insight_result.items() if not k.startswith("_")}
    career_summary = {k: v for k, v in career_result.items() if not k.startswith("_")}

    system = REPORT_SYSTEM_PROMPT.format(
        full_student_data=truncate_for_prompt(json.dumps(student_summary, indent=2), 1500),
        insight_data=truncate_for_prompt(json.dumps(insight_summary, indent=2), 1500),
        career_data=truncate_for_prompt(json.dumps(career_summary, indent=2), 1000),
    )

    cache_key = student_cache_key(student_id, normalized) + ":report"

    result = call_llm(
        task="report",
        system_prompt=system,
        user_prompt="Generate the complete student report.",
        cache_key=cache_key,
        estimated_tokens=2000,
    )

    if not isinstance(result, dict):
        result = {
            "executive_summary": str(result)[:300] if result else "Report generation failed.",
            "academic_analysis": "",
            "personal_development": "",
            "counselor_notes": "",
            "parent_message": "",
            "action_plan": [],
        }

    # Guardrails
    is_valid, issues, result = validate_report(result)
    result["_validation_issues"] = issues
    result["_valid"] = is_valid
    result["_student_name"] = normalized.get("name", "Student")
    result["_student_id"] = student_id

    return result
