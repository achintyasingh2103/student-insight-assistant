"""
agents/ingestion_agent.py
Agent 1 — validates, normalizes, and summarizes incoming student data.
Uses Groq 8b (fast, light task).
"""

import json
from llm.router import call_llm
from guardrails.input_validator import validate_student
from utils.prompts import INGESTION_SYSTEM_PROMPT
from utils.helpers import student_cache_key, format_score_summary


def run(student_data: dict) -> dict:
    """
    Validate and normalize student data.
    Returns enriched state dict with validation results.
    """
    # Guardrails: structural validation first (no LLM needed)
    is_valid, flags, normalized = validate_student(student_data)

    if not is_valid:
        return {
            "valid": False,
            "flags": flags,
            "normalized_data": normalized,
            "summary": "Validation failed — see flags.",
        }

    # Build a compact profile summary via LLM for downstream agents
    score_summary = format_score_summary(normalized["subjects"])
    user_prompt = f"""
Student: {normalized.get('name')} | Class {normalized.get('class')}{normalized.get('section', '')}
Attendance: {normalized.get('attendance_percent')}%
Subjects:\n{score_summary}
Extracurricular: {', '.join(normalized.get('extracurricular', []))}
Teacher remarks: {normalized.get('teacher_remarks', 'N/A')}
Behavioral: {normalized.get('behavioral_observations', 'N/A')}
Interests: {normalized.get('interests', 'N/A')}
"""

    cache_key = student_cache_key(normalized.get("id", "unknown"), normalized) + ":ingestion"

    result = call_llm(
        task="ingestion",
        system_prompt=INGESTION_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        cache_key=cache_key,
        estimated_tokens=400,
    )

    if isinstance(result, dict):
        result["flags"] = flags
        result["normalized_data"] = normalized
        return result

    # Fallback if LLM returns plain text
    return {
        "valid": True,
        "normalized_data": normalized,
        "flags": flags,
        "summary": str(result)[:300],
    }
