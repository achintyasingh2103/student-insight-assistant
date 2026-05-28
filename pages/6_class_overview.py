"""
pages/6_class_overview.py
Page 6 — Multi-student class overview and cohort comparison.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from utils.helpers import load_students, archetype_emoji

st.set_page_config(page_title="Class Overview | Student Insight", page_icon="🏫", layout="wide")
st.title("🏫 Class Overview")

students = st.session_state.get("students", [])
if not students:
    st.info("👈 Go to Upload / Input and load a dataset first.")
    st.stop()

# ── Build summary dataframe ───────────────────────────────────────────────────
rows = []
for s in students:
    subjects = s.get("subjects", {})
    avg = sum(subjects.values()) / len(subjects) if subjects else 0
    rows.append({
        "ID": s.get("id"),
        "Name": s.get("name"),
        "Class": s.get("class"),
        "Archetype": s.get("archetype", "—"),
        "Avg Score": round(avg, 1),
        "Attendance %": s.get("attendance_percent", 0),
        **{subj: score for subj, score in subjects.items()},
    })

df = pd.DataFrame(rows)

# ── Filters ───────────────────────────────────────────────────────────────────
col_f1, col_f2 = st.columns(2)
selected_class = col_f1.multiselect("Filter by class", sorted(df["Class"].unique()), default=sorted(df["Class"].unique()))
selected_arch = col_f2.multiselect("Filter by archetype", sorted(df["Archetype"].unique()), default=sorted(df["Archetype"].unique()))

filtered = df[df["Class"].isin(selected_class) & df["Archetype"].isin(selected_arch)]

st.markdown(f"Showing **{len(filtered)}** students")
st.dataframe(filtered[["ID", "Name", "Class", "Archetype", "Avg Score", "Attendance %"]].sort_values("Avg Score", ascending=False),
             use_container_width=True, hide_index=True)

st.divider()

# ── Charts ────────────────────────────────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.markdown("#### Archetype Distribution")
    arch_counts = filtered["Archetype"].value_counts().reset_index()
    arch_counts.columns = ["Archetype", "Count"]
    fig_pie = px.pie(arch_counts, names="Archetype", values="Count",
                     color_discrete_sequence=px.colors.qualitative.Set2)
    fig_pie.update_layout(height=320, margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig_pie, use_container_width=True)

with col2:
    st.markdown("#### Score Distribution")
    fig_hist = px.histogram(filtered, x="Avg Score", nbins=15,
                            color_discrete_sequence=["#1D9E75"])
    fig_hist.update_layout(height=320, margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig_hist, use_container_width=True)

# ── Scatter: Score vs Attendance ──────────────────────────────────────────────
st.markdown("#### Score vs Attendance by Archetype")
fig_scatter = px.scatter(
    filtered, x="Attendance %", y="Avg Score",
    color="Archetype", hover_data=["Name", "Class"],
    color_discrete_sequence=px.colors.qualitative.Set2,
    size_max=12,
)
fig_scatter.update_layout(height=380, margin=dict(l=0, r=0, t=0, b=0))
st.plotly_chart(fig_scatter, use_container_width=True)

# ── Bottom performers alert ───────────────────────────────────────────────────
st.divider()
st.markdown("#### ⚠️ Students Needing Attention")
at_risk = filtered[(filtered["Avg Score"] < 55) | (filtered["Attendance %"] < 70)]
if at_risk.empty:
    st.success("No students flagged as at-risk with current filters.")
else:
    st.warning(f"{len(at_risk)} student(s) flagged (score < 55 or attendance < 70%)")
    st.dataframe(at_risk[["Name", "Class", "Archetype", "Avg Score", "Attendance %"]],
                 use_container_width=True, hide_index=True)
