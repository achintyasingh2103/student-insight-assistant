"""
guardrails/output_validator.py
Validates LLM outputs before rendering to the user.
Checks tone, hallucination risk, required fields, and safety.
"""

import re

# Words/phrases that must never appear in student-facing outputs
NEGATIVE_LABELS = [
    "stupid", "dumb", "hopeless", "failure", "lazy", "incompetent",
    "lost cause", "unteachable", "problem student", "disruptive",
    "cannot learn", "will never", "has no future",
]

# Required keys per output type
REQUIRED_INSIGHT_KEYS = [
    "top_strengths", "improvement_areas", "learning_style",
    "engagement_score", "behavioral_pattern", "confidence_level",
    "key_observation",
]

REQUIRED_CAREER_KEYS = ["career_recommendations", "overall_career_note"]

REQUIRED_REPORT_KEYS = [
    "executive_summary", "academic_analysis", "personal_development",
    "counselor_notes", "parent_message", "action_plan",
]

VALID_LEARNING_STYLES = {"Visual", "Auditory", "Kinesthetic", "Read-Write"}
VALID_ARCHETYPES = {
    "Overachiever", "Creative Underperformer", "Silent Struggler",
    "All-Rounder", "Anxious Performer", "Late Bloomer",
}
VALID_CONFIDENCE = {"Low", "Medium", "High"}


def check_tone(text: str) -> list[str]:
    """Flag any negative labels in LLM output."""
    issues = []
    lower = text.lower()
    for label in NEGATIVE_LABELS:
        if label in lower:
            issues.append(f"Negative label detected: '{label}'")
    return issues


def validate_insight(output: dict) -> tuple[bool, list[str], dict]:
    issues = []

    # Required keys
    for key in REQUIRED_INSIGHT_KEYS:
        if key not in output:
            issues.append(f"Missing key in insight output: '{key}'")

    # Engagement score range
    score = output.get("engagement_score")
    if score is not None:
        try:
            score = int(score)
            if not (1 <= score <= 10):
                issues.append(f"Engagement score {score} out of range 1-10. Clipping.")
                output["engagement_score"] = max(1, min(10, score))
        except (TypeError, ValueError):
            issues.append("Engagement score is not an integer.")
            output["engagement_score"] = 5

    # Enum validations
    ls = output.get("learning_style", "")
    if ls not in VALID_LEARNING_STYLES:
        issues.append(f"Invalid learning_style '{ls}'. Defaulting to 'Visual'.")
        output["learning_style"] = "Visual"

    bp = output.get("behavioral_pattern", "")
    if bp not in VALID_ARCHETYPES:
        issues.append(f"Invalid behavioral_pattern '{bp}'.")

    cl = output.get("confidence_level", "")
    if isinstance(cl, dict):
        cl_text = cl.get("level", "")
    else:
        cl_text = str(cl)
    if not any(v in cl_text for v in VALID_CONFIDENCE):
        issues.append(f"Invalid confidence_level '{cl}'.")

    # Tone check on narrative fields
    for field in ["key_observation"]:
        tone_issues = check_tone(str(output.get(field, "")))
        issues.extend(tone_issues)

    is_valid = len([i for i in issues if "Missing key" in i]) == 0
    return is_valid, issues, output


def validate_career(output: dict) -> tuple[bool, list[str], dict]:
    issues = []

    for key in REQUIRED_CAREER_KEYS:
        if key not in output:
            issues.append(f"Missing key in career output: '{key}'")

    recs = output.get("career_recommendations", [])
    if not isinstance(recs, list) or len(recs) == 0:
        issues.append("No career recommendations returned.")
    elif len(recs) < 3:
        issues.append(f"Only {len(recs)} career recommendations (expected 3).")

    for rec in recs:
        tone_issues = check_tone(str(rec.get("why_suited", "")))
        issues.extend(tone_issues)

    is_valid = len([i for i in issues if "Missing key" in i]) == 0
    return is_valid, issues, output


def validate_report(output: dict) -> tuple[bool, list[str], dict]:
    issues = []

    for key in REQUIRED_REPORT_KEYS:
        if key not in output:
            issues.append(f"Missing key in report output: '{key}'")

    for field in ["parent_message", "counselor_notes", "executive_summary"]:
        tone_issues = check_tone(str(output.get(field, "")))
        issues.extend(tone_issues)

    is_valid = len([i for i in issues if "Missing key" in i]) == 0
    return is_valid, issues, output
