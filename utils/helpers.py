"""
utils/helpers.py
Shared utility functions across the project.
"""

import json
import hashlib
import re
from typing import Any


def safe_json_parse(text: str) -> dict | list | None:
    """
    Safely parse LLM output that should be JSON.
    Strips markdown fences if present.
    """
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON block inside the text
        match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                return None
    return None


def student_cache_key(student_id: str, student_data: dict) -> str:
    """
    Generate a deterministic cache key from student ID + data hash.
    If data changes, cache is invalidated automatically.
    """
    data_str = json.dumps(student_data, sort_keys=True)
    data_hash = hashlib.md5(data_str.encode()).hexdigest()[:8]
    return f"student:{student_id}:{data_hash}"


def format_score_summary(subjects: dict) -> str:
    """Format subject scores into a readable summary string for prompts."""
    lines = [f"{subj}: {score}/100" for subj, score in subjects.items()]
    avg = sum(subjects.values()) / len(subjects)
    lines.append(f"Average: {avg:.1f}/100")
    return "\n".join(lines)


def engagement_color(score: int) -> str:
    """Map engagement score 1-10 to a display color."""
    if score >= 8:
        return "#1D9E75"   # teal
    elif score >= 5:
        return "#EF9F27"   # amber
    else:
        return "#D85A30"   # coral


def archetype_emoji(archetype: str) -> str:
    mapping = {
        "Overachiever": "🏆",
        "Creative Underperformer": "🎨",
        "Silent Struggler": "🌱",
        "All-Rounder": "⭐",
        "Anxious Performer": "🧠",
        "Late Bloomer": "🌻",
    }
    return mapping.get(archetype, "📚")


def truncate_for_prompt(text: str, max_chars: int = 2000) -> str:
    """Truncate long text to stay within token budgets."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "... [truncated]"


def load_students(path: str = "data/students.json") -> list[dict]:
    """Load the student dataset from disk."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("students", data if isinstance(data, list) else [])


def student_by_id(students: list[dict], student_id: str) -> dict | None:
    """Find a student by their ID."""
    for s in students:
        if s.get("id") == student_id:
            return s
    return None
