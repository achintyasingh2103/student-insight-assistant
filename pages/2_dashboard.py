"""
pages/2_dashboard.py
Page 2 — Visual dashboard showing scores, attendance, engagement.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from utils.helpers import archetype_emoji, engagement_color

st.set_page_config(page_title="Dashboard | Student Insight", page_icon="📊", layout="wide")
st.title("📊 Student Dashboard")


def _get_result():
    sid = st.session_state.get("selected_student_id")
    results = st.session_state.get("pipeline_results", {})
    if sid and sid in results:
        return results[sid]
    return None


result = _get_result()
if not result:
    st.info("👈 Go to Upload / Input and run an analysis first.")
    st.stop()

normalized = result["ingestion_result"]["normalized_data"]
insight = result["insight_result"]
name = normalized.get("name", "Student")
subjects = normalized.get("subjects", {})

# ── Top metrics ───────────────────────────────────────────────────────────────
archetype = insight.get("behavioral_pattern", "—")
engagement = insight.get("engagement_score", 5)
confidence = insight.get("confidence_level", "Medium")
if isinstance(confidence, dict):
    confidence = confidence.get("level", str(confidence))
avg_score = sum(subjects.values()) / len(subjects) if subjects else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("Student", name)
col2.metric("Avg Score", f"{avg_score:.1f}/100")
col3.metric("Attendance", f"{normalized.get('attendance_percent', 0)}%")
col4.metric("Engagement", f"{engagement}/10")

st.markdown(f"**Archetype:** {archetype_emoji(archetype)} {archetype}  |  **Confidence:** {confidence}  |  **Learning Style:** {insight.get('learning_style', '—')}")
st.divider()

# ── Charts row ────────────────────────────────────────────────────────────────
col_radar, col_bar = st.columns(2)

with col_radar:
    st.markdown("#### Subject Performance Radar")
    subj_labels = list(subjects.keys())
    subj_values = list(subjects.values())
    fig_radar = go.Figure(go.Scatterpolar(
        r=subj_values + [subj_values[0]],
        theta=subj_labels + [subj_labels[0]],
        fill="toself",
        fillcolor="rgba(29, 158, 117, 0.2)",
        line=dict(color="#1D9E75", width=2),
        name=name,
    ))
    fig_radar.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=False, height=320, margin=dict(l=20, r=20, t=20, b=20),
    )
    st.plotly_chart(fig_radar, use_container_width=True)

with col_bar:
    st.markdown("#### Score vs Class Average (estimated)")
    class_avg = [65, 62, 68, 70, 63]  # simulated class averages
    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(name=name, x=subj_labels, y=subj_values,
                             marker_color="#1D9E75"))
    fig_bar.add_trace(go.Bar(name="Class Avg", x=subj_labels, y=class_avg,
                             marker_color="#E5E7EB"))
    fig_bar.update_layout(barmode="group", height=320,
                          margin=dict(l=20, r=20, t=20, b=20),
                          legend=dict(orientation="h", yanchor="bottom", y=1.02))
    st.plotly_chart(fig_bar, use_container_width=True)

# ── Engagement gauge ──────────────────────────────────────────────────────────
col_gauge, col_info = st.columns(2)

with col_gauge:
    st.markdown("#### Engagement Score")
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=engagement,
        domain={"x": [0, 1], "y": [0, 1]},
        title={"text": "Engagement (1-10)"},
        gauge={
            "axis": {"range": [0, 10]},
            "bar": {"color": engagement_color(engagement)},
            "steps": [
                {"range": [0, 4], "color": "#FEE2E2"},
                {"range": [4, 7], "color": "#FEF3C7"},
                {"range": [7, 10], "color": "#D1FAE5"},
            ],
        },
    ))
    fig_gauge.update_layout(height=280, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig_gauge, use_container_width=True)

with col_info:
    st.markdown("#### Student Profile")
    extras = normalized.get("extracurricular", [])
    st.markdown(f"**Extracurricular:** {', '.join(extras) if extras else 'None recorded'}")
    st.markdown(f"**Teacher Remarks:**")
    st.info(normalized.get("teacher_remarks", "—"))
    st.markdown(f"**Key Observation:**")
    st.success(insight.get("key_observation", "—"))
