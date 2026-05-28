"""
data/generate_dataset.py
Hybrid synthetic dataset generator.
  Step 1 — NumPy + Faker generate all STRUCTURED fields instantly
  Step 2 — Single Groq batch call fills NARRATIVE fields (teacher_remarks,
            behavioral_observations, interests) for all students at once
  Step 3 — Merge and save to data/students.json

Run once:  python data/generate_dataset.py
"""

import json
import os
import random
import numpy as np
from faker import Faker
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

fake = Faker("en_IN")   # Indian locale for realistic names
rng = np.random.default_rng(42)

# ── Archetype definitions ────────────────────────────────────────────────────

ARCHETYPES = [
    {
        "name": "Overachiever",
        "count": 8,
        "score_range": (82, 99),
        "attendance_range": (88, 99),
        "score_variance": 5,
    },
    {
        "name": "Creative Underperformer",
        "count": 8,
        "score_range": (38, 58),
        "attendance_range": (60, 78),
        "score_variance": 18,
    },
    {
        "name": "Silent Struggler",
        "count": 8,
        "score_range": (42, 62),
        "attendance_range": (65, 80),
        "score_variance": 10,
    },
    {
        "name": "All-Rounder",
        "count": 8,
        "score_range": (68, 84),
        "attendance_range": (82, 95),
        "score_variance": 8,
    },
    {
        "name": "Anxious Performer",
        "count": 8,
        "score_range": (75, 94),
        "attendance_range": (85, 98),
        "score_variance": 6,
    },
    {
        "name": "Late Bloomer",
        "count": 10,
        "score_range": (55, 75),
        "attendance_range": (70, 88),
        "score_variance": 14,
    },
]

SUBJECTS = [
    "Mathematics",
    "Science",
    "English",
    "Hindi",
    "Social_Science",
]

CLASSES = ["9", "10", "11", "12"]
SECTIONS = ["A", "B", "C"]

EXTRACURRICULAR_POOL = {
    "Overachiever":           ["Science Olympiad", "Math Club", "Debate Team", "Model UN"],
    "Creative Underperformer": ["Painting", "Music Band", "Drama Club", "Sketching", "Photography"],
    "Silent Struggler":        ["Chess", "Library Club", "Gardening Club"],
    "All-Rounder":             ["Cricket", "Student Council", "Debate Team", "NCC", "Badminton"],
    "Anxious Performer":       ["Math Club", "Quiz Team", "Science Olympiad"],
    "Late Bloomer":            ["Football", "Yoga Club", "Environmental Club", "Craft Club"],
}

INDIAN_MALE_NAMES = [
    "Arjun Mehta", "Rohan Sharma", "Vivek Nair", "Karan Patel", "Aditya Singh",
    "Rahul Gupta", "Siddharth Joshi", "Nikhil Verma", "Pranav Rao", "Ishaan Kumar",
    "Dhruv Malhotra", "Yash Agarwal", "Arnav Bose", "Kabir Shah", "Varun Reddy",
    "Manav Iyer", "Shreyas Pillai", "Ansh Kapoor", "Dev Chauhan", "Rishi Mishra",
    "Parth Trivedi", "Akash Tiwari", "Harsh Saxena", "Mohit Pandey", "Gaurav Sinha",
]

INDIAN_FEMALE_NAMES = [
    "Ananya Krishnan", "Priya Sharma", "Kavya Nair", "Riya Patel", "Sneha Gupta",
    "Aditi Verma", "Tanvi Joshi", "Shreya Rao", "Diya Kumar", "Nisha Mehta",
    "Pooja Reddy", "Aisha Khan", "Meera Iyer", "Simran Kaur", "Ritu Agarwal",
    "Divya Pillai", "Sanya Shah", "Kriti Kapoor", "Aarohi Mishra", "Vidya Trivedi",
    "Swati Tiwari", "Bhavya Saxena", "Isha Pandey", "Suhani Sinha", "Palak Jain",
]

ALL_NAMES = INDIAN_MALE_NAMES + INDIAN_FEMALE_NAMES
random.shuffle(ALL_NAMES)


def _generate_scores(archetype: dict) -> dict:
    low, high = archetype["score_range"]
    base = rng.integers(low, high)
    scores = {}
    for subj in SUBJECTS:
        noise = int(rng.normal(0, archetype["score_variance"]))
        score = int(np.clip(base + noise, 0, 100))
        scores[subj] = score
    return scores


def _generate_structured_students() -> list[dict]:
    students = []
    student_id = 1
    name_pool = ALL_NAMES.copy()
    random.shuffle(name_pool)
    name_idx = 0

    for archetype in ARCHETYPES:
        for _ in range(archetype["count"]):
            name = name_pool[name_idx % len(name_pool)]
            name_idx += 1

            att_low, att_high = archetype["attendance_range"]
            attendance = round(float(rng.uniform(att_low, att_high)), 1)

            extracurriculars = random.sample(
                EXTRACURRICULAR_POOL[archetype["name"]],
                k=min(2, len(EXTRACURRICULAR_POOL[archetype["name"]])),
            )

            student = {
                "id": f"STU{student_id:03d}",
                "name": name,
                "class": random.choice(CLASSES),
                "section": random.choice(SECTIONS),
                "archetype": archetype["name"],
                "attendance_percent": attendance,
                "subjects": _generate_scores(archetype),
                "extracurricular": extracurriculars,
                # Narrative fields — filled by LLM in Step 2
                "teacher_remarks": "",
                "behavioral_observations": "",
                "interests": "",
            }
            students.append(student)
            student_id += 1

    return students


def _fill_narratives_via_llm(students: list[dict]) -> list[dict]:
    """
    Single Groq batch call to fill narrative fields for all students.
    Passes only the fields the LLM needs — not the full object.
    """
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    # Build compact context for each student
    compact = [
        {
            "id": s["id"],
            "name": s["name"],
            "archetype": s["archetype"],
            "class": s["class"],
            "attendance_percent": s["attendance_percent"],
            "avg_score": round(sum(s["subjects"].values()) / len(s["subjects"]), 1),
            "weakest_subject": min(s["subjects"], key=s["subjects"].get),
            "strongest_subject": max(s["subjects"], key=s["subjects"].get),
            "extracurricular": s["extracurricular"],
        }
        for s in students
    ]

    prompt = f"""
You are an experienced Indian school teacher and counselor with 15 years of experience.
For each student below, generate realistic narrative fields.

For EACH student produce:
1. teacher_remarks — 2-3 sentences from the class teacher, personal and observational
2. behavioral_observations — 2 sentences noting classroom behavior and social patterns
3. interests — 1-2 sentences describing genuine interests aligned with the archetype

RULES:
- Tone: professional, warm, constructive — never negative or labeling
- Must be INTERNALLY CONSISTENT with the student's archetype, scores, and attendance
- Use Indian school context: board exams, olympiads, school events, extracurriculars
- No repeated phrasing across students
- Return ONLY a valid JSON array, no markdown, no preamble

Students:
{json.dumps(compact, indent=2)}

Return format — JSON array, one object per student:
[
  {{
    "id": "STU001",
    "teacher_remarks": "...",
    "behavioral_observations": "...",
    "interests": "..."
  }}
]
"""

    print("  Calling Groq for narrative generation (single batch call)...")
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=8000,
    )

    raw = response.choices[0].message.content
    # Strip markdown fences if present
    raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()

    narratives = json.loads(raw)
    narrative_map = {n["id"]: n for n in narratives}

    # Merge narratives back into student records
    for student in students:
        sid = student["id"]
        if sid in narrative_map:
            student["teacher_remarks"] = narrative_map[sid].get("teacher_remarks", "")
            student["behavioral_observations"] = narrative_map[sid].get("behavioral_observations", "")
            student["interests"] = narrative_map[sid].get("interests", "")

    return students


def generate(output_path: str = "data/students.json") -> None:
    print("━━━ Student Dataset Generator ━━━")
    print("Step 1: Generating structured fields with NumPy + Faker...")
    students = _generate_structured_students()
    print(f"  ✓ {len(students)} students created across {len(ARCHETYPES)} archetypes")

    print("Step 2: Filling narrative fields via Groq (single batch call)...")
    try:
        students = _fill_narratives_via_llm(students)
        print("  ✓ Narrative fields populated")
    except Exception as e:
        print(f"  ⚠ LLM narrative generation failed: {e}")
        print("  Falling back to placeholder narratives...")
        for s in students:
            s["teacher_remarks"] = f"{s['name']} is a {s['archetype'].lower()} student showing consistent effort in class."
            s["behavioral_observations"] = "Participates in class activities. Gets along well with peers."
            s["interests"] = f"Shows interest in {', '.join(s['extracurricular'])}."

    print("Step 3: Saving dataset...")
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"students": students}, f, indent=2, ensure_ascii=False)

    print(f"  ✓ Saved {len(students)} students to {output_path}")
    print("\nArchetype distribution:")
    from collections import Counter
    counts = Counter(s["archetype"] for s in students)
    for arch, count in counts.items():
        print(f"  {arch:30s} {count} students")
    print("━━━ Done ━━━")


if __name__ == "__main__":
    generate()
