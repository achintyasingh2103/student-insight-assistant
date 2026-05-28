"""
agents/insight_agent.py
Agent 2 — deep educational insight analysis.
Uses NIM 70b (large prompt, quality critical).
"""

import json
from llm.router import call_llm
from guardrails.output_validator import validate_insight
from utils.prompts import INSIGHT_SYSTEM_PROMPT, INSIGHT_USER_PROMPT
from utils.helpers import student_cache_key, truncate_for_prompt


def run(ingestion_result: dict) -> dict:
    """
    Analyze normalized student data and generate educational insights.
    Returns validated insight dict.
    """
    normalized = ingestion_result.get("normalized_data", {})
    student_id = normalized.get("id", "unknown")

    student_data_str = json.dumps(normalized, indent=2, ensure_ascii=False)
    student_data_str = truncate_for_prompt(student_data_str, max_chars=3000)

    system = INSIGHT_SYSTEM_PROMPT.format(student_data=student_data_str)
    cache_key = student_cache_key(student_id, normalized) + ":insight"

    result = call_llm(
        task="insight",
        system_prompt=system,
        user_prompt=INSIGHT_USER_PROMPT,
        cache_key=cache_key,
        estimated_tokens=1200,
    )

    if not isinstance(result, dict):
        result = {
            "top_strengths": ["Data processing error"],
            "improvement_areas": [],
            "learning_style": "Visual",
            "engagement_score": 5,
            "behavioral_pattern": "All-Rounder",
            "confidence_level": "Medium",
            "key_observation": str(result)[:300] if result else "Could not generate insight.",
        }

    # Guardrails: validate and sanitize output
    is_valid, issues, result = validate_insight(result)
    result["_validation_issues"] = issues
    result["_valid"] = is_valid

    return result
