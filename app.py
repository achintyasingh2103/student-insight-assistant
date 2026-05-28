"""
app.py
Streamlit entry point for the AI-Powered Student Insight Assistant.
Run with: streamlit run app.py
"""

import streamlit as st

st.set_page_config(
    page_title="Student Insight Assistant",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎓 Student Insight Assistant")
    st.markdown("*Powered by Ekaakshar Education*")
    st.divider()
    st.markdown("### Navigation")
    st.page_link("pages/1_upload.py",        label="📤 Upload / Input",       icon="📤")
    st.page_link("pages/2_dashboard.py",     label="📊 Student Dashboard",    icon="📊")
    st.page_link("pages/3_insights.py",      label="🧠 Insight Report",       icon="🧠")
    st.page_link("pages/4_career.py",        label="🧭 Career Compass",       icon="🧭")
    st.page_link("pages/5_report.py",        label="📄 Full Report & PDF",    icon="📄")
    st.page_link("pages/6_class_overview.py",label="🏫 Class Overview",       icon="🏫")
    st.divider()

    # Live provider budget status
    st.markdown("### 🔌 Provider Status")
    try:
        from llm.rate_limiter import all_budget_status
        for status in all_budget_status():
            rpm_pct = (status["rpm_used"] / status["rpm_limit"] * 100) if isinstance(status["rpm_limit"], (int, float)) else 0
            st.caption(f"**{status['provider'].upper()}** — {status['rpm_used']}/{status['rpm_limit']} RPM")
            st.progress(min(rpm_pct / 100, 1.0))
    except Exception:
        st.caption("Provider status unavailable")

    st.divider()
    from llm.cache import cache_stats
    stats = cache_stats()
    st.caption(f"Cache: {stats['size']} entries | {stats['volume_bytes'] // 1024} KB")

# ── Home page ─────────────────────────────────────────────────────────────────
st.title("🎓 AI-Powered Student Insight Assistant")
st.markdown("""
Welcome to the **Ekaakshar Student Intelligence System** — an AI-powered platform that transforms
raw student data into actionable educational insights.

---

### How it works

| Step | Agent | What it does |
|------|-------|-------------|
| 1 | **Ingestion Agent** | Validates and normalizes your student data |
| 2 | **Insight Analyst** | Identifies strengths, gaps, and learning patterns |
| 3 | **Career Advisor** | Recommends career pathways using Indian education context |
| 4 | **Report Generator** | Produces a full narrative report for teachers and parents |

---

### Get started
👈 Use the sidebar to navigate, or click **Upload / Input** to begin.
""")

col1, col2, col3 = st.columns(3)
col1.metric("Students in Dataset", "50")
col2.metric("Career Pathways", "8 domains")
col3.metric("Report Formats", "Teacher + Parent")
