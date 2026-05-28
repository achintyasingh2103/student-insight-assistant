"""
agents/career_agent.py
Agent 3 — RAG-grounded career recommendations.
Retrieves relevant career knowledge then uses NIM llama-4 for reasoning.
"""

import json
from llm.router import call_llm
from guardrails.output_validator import validate_career
from rag.vector_store import retrieve
from utils.prompts import CAREER_SYSTEM_PROMPT
from utils.helpers import student_cache_key, truncate_for_prompt


def _build_rag_query(normalized: dict, insight: dict) -> str:
    """Build a targeted RAG query from student profile."""
    subjects = normalized.get("subjects", {})
    strong = [s for s, v in subjects.items() if v >= 70]
    extracurricular = normalized.get("extracurricular", [])
    archetype = insight.get("behavioral_pattern", "")
    interests = normalized.get("interests", "")

    return (
        f"Career pathways for student strong in {', '.join(strong) or 'general subjects'}. "
        f"Extracurricular: {', '.join(extracurricular)}. "
        f"Archetype: {archetype}. Interests: {interests}"
    )


def run(ingestion_result: dict, insight_result: dict) -> dict:
    """
    Generate RAG-grounded career recommendations.
    Returns validated career recommendations dict.
    """
    normalized = ingestion_result.get("normalized_data", {})
    student_id = normalized.get("id", "unknown")

    # Retrieve relevant context from knowledge base
    rag_query = _build_rag_query(normalized, insight_result)
    rag_context = retrieve(rag_query, n_results=4)

    # Build compact insight summary for prompt (avoid token bloat)
    insight_summary = {
        "top_strengths": insight_result.get("top_strengths", []),
        "improvement_areas": insight_result.get("improvement_areas", []),
        "learning_style": insight_result.get("learning_style"),
        "engagement_score": insight_result.get("engagement_score"),
        "behavioral_pattern": insight_result.get("behavioral_pattern"),
        "confidence_level": insight_result.get("confidence_level"),
    }

    system = CAREER_SYSTEM_PROMPT.format(
        rag_context=truncate_for_prompt(rag_context, 2000),
        insight_data=json.dumps(insight_summary, indent=2),
    )

    cache_key = student_cache_key(student_id, normalized) + ":career"

    result = call_llm(
        task="career",
        system_prompt=system,
        user_prompt="Generate career recommendations for this student.",
        cache_key=cache_key,
        estimated_tokens=1500,
    )

    if not isinstance(result, dict):
        result = {
            "career_recommendations": [],
            "overall_career_note": str(result)[:300] if result else "Could not generate recommendations.",
        }

    # Guardrails
    is_valid, issues, result = validate_career(result)
    result["_validation_issues"] = issues
    result["_valid"] = is_valid

    return result
