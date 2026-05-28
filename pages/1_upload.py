"""
pages/1_upload.py
Page 1 — Upload CSV or enter student data manually.
Triggers the full agent pipeline on submission.
"""

import streamlit as st
import json
import pandas as pd
from pathlib import Path
from agents.orchestrator import run_pipeline
from utils.helpers import load_students

st.set_page_config(page_title="Upload | Student Insight", page_icon="📤", layout="wide")
st.title("📤 Upload / Input Student Data")

if "pipeline_results" not in st.session_state:
    st.session_state.pipeline_results = {}
if "students" not in st.session_state:
    st.session_state.students = []

# ── Load existing dataset ─────────────────────────────────────────────────────
dataset_path = Path("data/students.json")
tab1, tab2, tab3 = st.tabs(["📂 Load Dataset", "📊 Upload CSV", "✏️ Manual Entry"])

with tab1:
    st.markdown("### Load the pre-generated student dataset")
    if dataset_path.exists():
        if st.button("Load students.json", type="primary"):
            students = load_students(str(dataset_path))
            st.session_state.students = students
            st.success(f"✅ Loaded {len(students)} students from dataset")
    else:
        st.warning("⚠️ No dataset found. Run `python data/generate_dataset.py` first.")
        if st.button("Generate dataset now (requires GROQ_API_KEY)"):
            with st.spinner("Generating dataset... this may take 30-60 seconds"):
                try:
                    from data.generate_dataset import generate
                    generate()
                    st.success("Dataset generated!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Generation failed: {e}")

with tab2:
    st.markdown("### Upload a CSV file")
    st.markdown("Required columns: `name`, `class`, `section`, `attendance_percent`, subject score columns")
    uploaded = st.file_uploader("Upload CSV", type=["csv"])
    if uploaded:
        df = pd.read_csv(uploaded)
        st.dataframe(df.head(10))
        if st.button("Use this CSV"):
            subject_cols = [c for c in df.columns if c not in
                           ["id", "name", "class", "section", "attendance_percent",
                            "extracurricular", "teacher_remarks", "behavioral_observations",
                            "interests", "archetype"]]
            students = []
            for i, row in df.iterrows():
                s = {
                    "id": str(row.get("id", f"STU{i+1:03d}")),
                    "name": str(row.get("name", f"Student {i+1}")),
                    "class": str(row.get("class", "10")),
                    "section": str(row.get("section", "A")),
                    "attendance_percent": float(row.get("attendance_percent", 80)),
                    "subjects": {col: float(row.get(col, 0)) for col in subject_cols},
                    "extracurricular": str(row.get("extracurricular", "")).split(","),
                    "teacher_remarks": str(row.get("teacher_remarks", "")),
                    "behavioral_observations": str(row.get("behavioral_observations", "")),
                    "interests": str(row.get("interests", "")),
                    "archetype": str(row.get("archetype", "All-Rounder")),
                }
                students.append(s)
            st.session_state.students = students
            st.success(f"✅ Loaded {len(students)} students from CSV")

with tab3:
    st.markdown("### Enter a single student manually")
    with st.form("manual_entry"):
        c1, c2, c3 = st.columns(3)
        name = c1.text_input("Student Name", "Arjun Mehta")
        cls = c2.selectbox("Class", ["9", "10", "11", "12"])
        section = c3.selectbox("Section", ["A", "B", "C"])
        attendance = st.slider("Attendance %", 0, 100, 82)

        st.markdown("**Subject Scores**")
        sc1, sc2, sc3, sc4, sc5 = st.columns(5)
        math  = sc1.number_input("Mathematics", 0, 100, 74)
        sci   = sc2.number_input("Science", 0, 100, 68)
        eng   = sc3.number_input("English", 0, 100, 80)
        hindi = sc4.number_input("Hindi", 0, 100, 72)
        soc   = sc5.number_input("Social Science", 0, 100, 65)

        extras = st.multiselect("Extracurricular", [
            "Cricket", "Debate Team", "Science Olympiad", "Music Band",
            "Student Council", "NCC", "Drama Club", "Chess", "Painting",
        ])
        remarks = st.text_area("Teacher Remarks", "Shows consistent effort in class.")
        interests = st.text_input("Interests", "Technology and sports")

        submitted = st.form_submit_button("Add Student", type="primary")
        if submitted:
            student = {
                "id": "MANUAL001",
                "name": name, "class": cls, "section": section,
                "attendance_percent": float(attendance),
                "subjects": {
                    "Mathematics": math, "Science": sci, "English": eng,
                    "Hindi": hindi, "Social_Science": soc,
                },
                "extracurricular": extras,
                "teacher_remarks": remarks,
                "behavioral_observations": "",
                "interests": interests,
                "archetype": "All-Rounder",
            }
            st.session_state.students = [student]
            st.success(f"✅ Added {name}")

# ── Student selector + pipeline trigger ──────────────────────────────────────
st.divider()
if st.session_state.students:
    st.markdown(f"### Loaded: {len(st.session_state.students)} students")

    student_names = [f"{s['id']} — {s['name']}" for s in st.session_state.students]
    selected_label = st.selectbox("Select a student to analyze", student_names)
    selected_idx = student_names.index(selected_label)
    selected_student = st.session_state.students[selected_idx]

    st.json(selected_student, expanded=False)

    if st.button("🚀 Run Full AI Analysis", type="primary"):
        student_id = selected_student.get("id", "unknown")
        with st.status("Running agent pipeline...", expanded=True) as status:
            st.write("🔍 Agent 1: Validating data...")
            try:
                result = run_pipeline(selected_student)
                st.write("🧠 Agent 2: Generating insights...")
                st.write("🧭 Agent 3: Building career recommendations...")
                st.write("📄 Agent 4: Writing report...")
                st.session_state.pipeline_results[student_id] = result
                st.session_state.selected_student_id = student_id
                status.update(label="✅ Analysis complete!", state="complete")
                st.success("Navigate to Dashboard, Insights, Career Compass, or Report pages.")
            except Exception as e:
                status.update(label="❌ Analysis failed", state="error")
                st.error(f"Pipeline error: {e}")
