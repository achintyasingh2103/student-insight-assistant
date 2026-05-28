"""
guardrails/input_validator.py
Validates and sanitizes incoming student data before any LLM processing.
"""

from typing import Tuple

REQUIRED_FIELDS = ["name", "class", "subjects", "attendance_percent"]
SUBJECT_SCORE_RANGE = (0, 100)
ATTENDANCE_RANGE = (0, 100)
MAX_TEXT_LENGTH = 500


def validate_student(data: dict) -> Tuple[bool, list[str], dict]:
    """
    Returns (is_valid, list_of_flags, normalized_data).
    Normalizes what it can; flags what it cannot fix.
    """
    flags = []
    normalized = data.copy()

    # Required field check
    for field in REQUIRED_FIELDS:
        if field not in data or data[field] is None:
            flags.append(f"Missing required field: '{field}'")

    if flags:
        return False, flags, normalized

    # Attendance range
    att = data.get("attendance_percent", 0)
    try:
        att = float(att)
        if not (ATTENDANCE_RANGE[0] <= att <= ATTENDANCE_RANGE[1]):
            flags.append(f"Attendance {att}% out of valid range 0-100. Clipping.")
            att = max(0.0, min(100.0, att))
        normalized["attendance_percent"] = round(att, 1)
    except (TypeError, ValueError):
        flags.append("Attendance value is not a number. Defaulting to 0.")
        normalized["attendance_percent"] = 0.0

    # Subject score ranges
    subjects = data.get("subjects", {})
    normalized_subjects = {}
    for subj, score in subjects.items():
        try:
            score = float(score)
            if not (SUBJECT_SCORE_RANGE[0] <= score <= SUBJECT_SCORE_RANGE[1]):
                flags.append(f"Score for {subj} ({score}) out of range. Clipping.")
                score = max(0.0, min(100.0, score))
            normalized_subjects[subj] = round(score, 1)
        except (TypeError, ValueError):
            flags.append(f"Score for {subj} is not a number. Setting to 0.")
            normalized_subjects[subj] = 0.0
    normalized["subjects"] = normalized_subjects

    # Text field length caps (prevent prompt injection via long inputs)
    for text_field in ["teacher_remarks", "behavioral_observations", "interests"]:
        if text_field in normalized and isinstance(normalized[text_field], str):
            if len(normalized[text_field]) > MAX_TEXT_LENGTH:
                flags.append(f"Field '{text_field}' truncated to {MAX_TEXT_LENGTH} chars.")
                normalized[text_field] = normalized[text_field][:MAX_TEXT_LENGTH]

    # Name sanitization
    name = str(normalized.get("name", "")).strip()
    if len(name) < 2:
        flags.append("Name too short or missing.")
    normalized["name"] = name[:100]

    is_valid = not any("Missing required" in f for f in flags)
    return is_valid, flags, normalized
