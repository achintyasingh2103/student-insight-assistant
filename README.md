# 🎓 AI-Powered Student Insight Assistant

Student Insight Assistant is a Streamlit-based, multi-agent AI system that turns raw student records into teacher-friendly insights, career guidance, and downloadable reports. It is designed around an Indian school context, with synthetic CBSE-style data, contextual career recommendations, validation guardrails, and a provider fallback chain for LLM calls.

The project is meant to demonstrate how AI can help teachers, counselors, and parents move from scattered academic data to practical next steps: strengths, risks, engagement patterns, learning style signals, career directions, and parent-safe summaries.

---

## ✨ What the Project Does

- Loads a pre-generated dataset of 50 synthetic students or accepts CSV/manual input.
- Validates student records before sending them into the AI pipeline.
- Runs a 4-agent LangGraph workflow:
  - **Ingestion Agent** cleans and normalizes student data.
  - **Insight Analyst** identifies academic strengths, gaps, behavioral signals, learning style, and engagement level.
  - **Career Advisor** uses RAG over a small career knowledge base to suggest suitable pathways.
  - **Report Generator** creates a structured narrative report for teachers and parents.
- Uses an LLM router with provider fallbacks across Groq, NVIDIA NIM, Gemini, and Anthropic.
- Tracks provider request budgets in a rolling 60-second window.
- Caches structured LLM responses with `diskcache` to reduce repeat calls and avoid unnecessary rate-limit pressure.
- Generates teacher and parent PDF reports using ReportLab.
- Provides dashboards and class-level views using Streamlit and Plotly.

---

## 🏗️ Architecture

```
Streamlit Frontend (6 pages)
        ↓
LangGraph Orchestrator (state machine)
        ↓
┌──────────┬──────────┬──────────┬──────────┐
│ Agent 1  │ Agent 2  │ Agent 3  │ Agent 4  │
│ Ingest   │ Insight  │ Career   │ Report   │
│          │ Analyst  │ Advisor  │ Generator│
└──────────┴──────────┴──────────┴──────────┘
        ↓
Guardrails Layer (input + output validation)
        ↓
LLM Router (Groq → NIM → Gemini → Claude Haiku)
        ↓
ChromaDB RAG + diskcache + Synthetic Dataset
```

---

## 🚀 Quick Start

### 1. Clone and install

```bash
git clone <your-repo>
cd student-insight-assistant
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Set up environment variables

Create a `.env` file in the project root:

```bash
GROQ_API_KEY=your_groq_key
NVIDIA_API_KEY=your_nvidia_key
GOOGLE_API_KEY=your_google_key
ANTHROPIC_API_KEY=your_anthropic_key
```

Required for the intended routing:
- `GROQ_API_KEY` — used for fast ingestion, guardrails, and dataset generation.
- `NVIDIA_API_KEY` — used for heavier insight, career, and report-generation tasks through NVIDIA NIM.

Optional fallbacks:
- `GOOGLE_API_KEY` — used by Gemini Flash when earlier providers fail or hit budget limits.
- `ANTHROPIC_API_KEY` — used as a final fallback through Claude Haiku.

The app can start without every optional key, but any provider without a working key will fail when selected by the router.

### 3. Generate or load the student dataset

The repository includes `data/students.json` with 50 synthetic students. If you need to regenerate it:

```bash
python data/generate_dataset.py
```

Dataset generation uses structured NumPy/Faker fields plus a Groq call for narrative fields such as teacher remarks, behavioral observations, and interests. Run it sparingly because it consumes LLM quota.

### 4. Launch the app

```bash
streamlit run app.py
```

Open the local Streamlit URL, then use **Upload / Input** to load `students.json`, upload a CSV, or enter one student manually.

---

## 🧭 App Pages

| Page | Purpose |
|------|---------|
| Upload / Input | Load the bundled dataset, upload a CSV, or manually enter one student. |
| Student Dashboard | View academic and engagement summaries for the selected student. |
| Insight Report | Read AI-generated strengths, risks, patterns, and intervention suggestions. |
| Career Compass | Explore RAG-backed career recommendations for the student profile. |
| Full Report & PDF | Generate report text and download teacher/parent PDF versions. |
| Class Overview | Compare students at a class level and identify broader trends. |

---

## 📁 Project Structure

```
student-insight-assistant/
├── app.py                          # Streamlit entry point
├── requirements.txt
│
├── agents/
│   ├── orchestrator.py             # LangGraph state machine
│   ├── ingestion_agent.py          # Agent 1: normalize and validate data
│   ├── insight_agent.py            # Agent 2: learning insights
│   ├── career_agent.py             # Agent 3: RAG career recommendations
│   └── report_agent.py             # Agent 4: narrative report generation
│
├── llm/
│   ├── router.py                   # Provider abstraction + fallback chain
│   ├── cache.py                    # diskcache response cache
│   └── rate_limiter.py             # Rolling RPM/TPM budget tracker
│
├── guardrails/
│   ├── input_validator.py          # Schema, range, text, and PII validation
│   └── output_validator.py         # JSON shape, score, enum, and tone checks
│
├── rag/
│   ├── knowledge_base/             # Markdown career/learning knowledge docs
│   └── vector_store.py             # ChromaDB setup + retrieval
│
├── data/
│   ├── generate_dataset.py         # Synthetic student dataset generator
│   └── students.json               # Pre-generated 50-student dataset
│
├── reports/
│   └── pdf_generator.py            # ReportLab PDF builder
│
├── utils/
│   ├── prompts.py                  # Centralized agent prompts
│   └── helpers.py                  # Shared utility functions
│
└── pages/
    ├── 1_upload.py
    ├── 2_dashboard.py
    ├── 3_insights.py
    ├── 4_career.py
    ├── 5_report.py
    └── 6_class_overview.py
```

---

## 🤖 LLM Provider Strategy

| Task | Primary | Fallback 1 | Fallback 2 | Last Resort |
|------|---------|------------|------------|-------------|
| Ingestion / Guardrails | Groq 8b | NIM 70b | Gemini Flash | Claude Haiku |
| Insight Analysis | NIM 70b | Groq 70b | Gemini Flash | Claude Haiku |
| Career Advisor | NIM 70b | Groq 70b | Gemini Flash | Claude Haiku |
| Report Generation | NIM Nemotron | Groq 70b | Gemini Flash | Claude Haiku |
| Dataset Generation | Groq 70b | NIM 70b | Gemini Flash | Claude Haiku |

The router chooses the task's primary provider first, then falls through the configured fallback chain if the provider is over the local budget or raises an error.

**Why this routing:**
- **Groq** is fast and works well for lighter structured tasks.
- **NVIDIA NIM** is used for heavier reasoning/report tasks because it is configured with no local TPM ceiling.
- **Gemini Flash** is useful as a high-token fallback.
- **Claude Haiku** is treated as a final fallback, especially when the free providers are unavailable.

---

## 🧱 Rate Limits and Free-Tier Limitations

This project is intentionally built to work with free or low-cost LLM access, but free-tier model limits are the main practical limitation.

Current local budget settings in `llm/rate_limiter.py`:

| Provider | Local RPM Limit | Local TPM Limit |
|----------|-----------------|-----------------|
| Groq | 30 requests/min | 6,000 tokens/min |
| NVIDIA NIM | 40 requests/min | No local token cap |
| Gemini | 60 requests/min | 1,000,000 tokens/min |
| Anthropic | 50 requests/min | 100,000 tokens/min |

Important notes:
- These are **local safety budgets**, not guaranteed provider-side quotas. Actual free-tier limits can be lower, change over time, or vary by account/model.
- A full analysis for one student can trigger multiple LLM calls across ingestion, insight, career, and report generation. Running many students back-to-back can quickly hit free-tier request limits.
- Groq free-tier models are especially easy to exhaust when generating datasets or repeatedly running full reports, because narrative prompts can consume several thousand tokens.
- If a provider hits a rate limit, the router tries the next fallback. If all providers are unavailable, the app raises an "All LLM providers exhausted" error.
- The sidebar provider status shows local rolling request usage, but it cannot see provider-side account limits already consumed outside this app.
- Cached responses reduce repeat calls only when the same cache key and structured result are reused.
- PDF generation itself is local, but the report content must already exist from the LLM pipeline.

Suggested ways to reduce rate-limit issues:
- Analyze one student at a time during demos.
- Prefer the bundled `data/students.json` instead of regenerating the dataset repeatedly.
- Keep CSV batches small when testing.
- Wait 60 seconds after provider exhaustion before retrying.
- Add paid keys or higher-tier API keys for more reliable demos.
- Use caching during repeated demos with the same students.

---

## 🛡️ Guardrails

**Input validation:**
- Required field checks.
- Score range validation from 0 to 100.
- Attendance range validation.
- Text field length caps to reduce prompt-injection and runaway prompt risk.
- Basic PII sanitization.

**Output validation:**
- Required JSON key checks per agent.
- Engagement score range checks from 1 to 10.
- Enum validation for fields such as learning style, archetype, and confidence.
- Tone checks for banned negative labels.
- Hallucination risk flagging when outputs include unsupported claims.

Guardrails reduce obvious failures, but they do not make the system suitable for high-stakes automated decisions. Teacher/counselor review is still required.

---

## 📊 Student Dataset

The bundled dataset contains 50 synthetic students across 6 archetypes:

- Overachiever
- Creative Underperformer
- Silent Struggler
- All-Rounder
- Anxious Performer
- Late Bloomer

It uses an Indian school context with CBSE-style subjects, Indian names, board-exam references, realistic extracurriculars, teacher remarks, behavioral observations, and interest signals.

---

## 📄 PDF Reports

Two report formats are generated with ReportLab:

- **Teacher Edition** — includes detailed analysis, counselor-style notes, risks, and recommended interventions.
- **Parent Edition** — uses warmer language, avoids jargon, and focuses on supportive next steps.

---

## 🧪 Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Streamlit |
| Orchestration | LangGraph |
| LLM Providers | Groq, NVIDIA NIM, Gemini, Anthropic |
| RAG | ChromaDB + sentence-transformers |
| Caching | diskcache |
| Retry / Backoff | tenacity |
| PDF | ReportLab |
| Charts | Plotly |
| Data | Pandas, NumPy, Faker |
| Environment | python-dotenv |

---

## ⚠️ Known Limitations

- The app is a prototype/demo and should not be used as the sole basis for academic or career decisions.
- The dataset is synthetic, so insights demonstrate workflow capability rather than real-world predictive validity.
- LLM responses may vary between runs and can still contain errors despite guardrails.
- Provider availability depends on valid API keys and live external services.
- Free-tier API rate limits can interrupt full-pipeline analysis, especially when running many students or generating long reports.
- The local rate limiter reduces pressure but does not perfectly mirror provider-side quota enforcement.
- The RAG knowledge base is intentionally small and should be expanded for production use.
- CSV upload expects recognizable columns and may need preprocessing for real school exports.
- No authentication, role-based access, audit logging, or production data privacy controls are included.
- ChromaDB/cache files are stored locally under `.cache`, so results are machine-local.

---

## 🔧 Troubleshooting

**"All LLM providers exhausted"**

Usually means every configured provider either hit a local/provider rate limit or failed due to a missing/invalid key. Wait a minute, check `.env`, and retry with a smaller workload.

**Dataset generation fails**

Check `GROQ_API_KEY`, then avoid regenerating repeatedly. The included `data/students.json` is enough for normal demos.

**Career recommendations are empty**

Make sure the RAG knowledge base files exist under `rag/knowledge_base/` and the vector store can initialize ChromaDB locally.

**PDF is missing content**

Run the full AI analysis first. The PDF generator depends on completed insight, career, and report results in Streamlit session state.

---

