import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# =============================================================================
# main.py  —  Resume Analyzer · Guided Wizard UI
# =============================================================================
# Run with: streamlit run main.py
# =============================================================================

import tempfile
import streamlit as st
from dotenv import load_dotenv

from modules.file_parser          import parse_resume
from modules.skills_extractor     import extract_skills
from modules.experience_extractor import extract_experience
from modules.education_extractor  import extract_education
from modules.jd_matcher           import match_resume_to_jd
from modules.report_generator     import generate_report
from modules.email_agent          import send_report_email

load_dotenv()

# ── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Resume Analyzer",
    page_icon="📄",
    layout="centered",
)

# ── Session state defaults ─────────────────────────────────────────────────
for key, default in {
    "step":             1,
    "candidate_name":   "",
    "candidate_email":  "",
    "job_title":        "",
    "resume_file":      None,
    "jd_text":          "",
    "results":          None,
    "html_report":      None,
    "email_sent":       False,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ── Global CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">

<style>
/* ── Reset & base ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, [data-testid="stAppViewContainer"] {
  background: #f5f4f0 !important;
  font-family: 'DM Sans', sans-serif !important;
}

[data-testid="stAppViewContainer"] > .main {
  background: #f5f4f0 !important;
  padding: 0 !important;
}

/* Hide Streamlit chrome */
#MainMenu, footer, header,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"] { display: none !important; }

/* ── Top bar ── */
.topbar {
  position: sticky;
  top: 0;
  z-index: 999;
  background: #ffffff;
  border-bottom: 1px solid #e8e6e0;
  padding: 0 32px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 48px;
}
.topbar-brand {
  font-family: 'DM Sans', sans-serif;
  font-size: 17px;
  font-weight: 700;
  color: #1a1a1a;
  letter-spacing: -0.02em;
}
.topbar-brand span {
  display: inline-block;
  width: 28px; height: 28px;
  background: #16a34a;
  border-radius: 6px;
  margin-right: 8px;
  vertical-align: middle;
  line-height: 28px;
  text-align: center;
  font-size: 14px;
}
.step-pills {
  display: flex;
  gap: 6px;
  align-items: center;
}
.pill {
  width: 28px; height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  transition: all 0.2s ease;
}
.pill-done   { background: #1a1a1a; color: #fff; }
.pill-active { background: #16a34a; color: #fff; box-shadow: 0 0 0 3px #bbf7d0; }
.pill-todo   { background: #f0ede6; color: #9ca3af; }
.pill-connector {
  width: 20px; height: 1px;
  background: #e8e6e0;
}

/* ── Main card ── */
.card {
  background: #ffffff;
  border-radius: 16px;
  border: 1px solid #e8e6e0;
  padding: 48px 48px 40px;
  max-width: 620px;
  margin: 0 auto 24px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 4px 16px rgba(0,0,0,0.04);
}

/* ── Step label ── */
.step-label {
  font-family: 'DM Mono', monospace;
  font-size: 11px;
  font-weight: 500;
  color: #16a34a;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  margin-bottom: 12px;
}

/* ── Step title ── */
.step-title {
  font-size: 26px;
  font-weight: 700;
  color: #1a1a1a;
  letter-spacing: -0.03em;
  line-height: 1.2;
  margin-bottom: 8px;
}

/* ── Step subtitle ── */
.step-sub {
  font-size: 14px;
  color: #6b7280;
  line-height: 1.6;
  margin-bottom: 36px;
}

/* ── Input overrides ── */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {
  font-family: 'DM Sans', sans-serif !important;
  font-size: 15px !important;
  border: 1.5px solid #e8e6e0 !important;
  border-radius: 10px !important;
  padding: 13px 16px !important;
  background: #fafaf9 !important;
  color: #1a1a1a !important;
  transition: border-color 0.15s ease, box-shadow 0.15s ease !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
  border-color: #16a34a !important;
  box-shadow: 0 0 0 3px rgba(22,163,74,0.12) !important;
  outline: none !important;
}
[data-testid="stTextInput"] label,
[data-testid="stTextArea"] label,
[data-testid="stFileUploader"] label {
  font-family: 'DM Sans', sans-serif !important;
  font-size: 13px !important;
  font-weight: 600 !important;
  color: #374151 !important;
  margin-bottom: 6px !important;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
  border: 2px dashed #d1d5db !important;
  border-radius: 12px !important;
  padding: 32px !important;
  background: #fafaf9 !important;
  text-align: center !important;
  transition: border-color 0.2s ease !important;
}
[data-testid="stFileUploader"]:hover {
  border-color: #16a34a !important;
}

/* ── Buttons ── */
[data-testid="stButton"] > button {
  font-family: 'DM Sans', sans-serif !important;
  font-size: 15px !important;
  font-weight: 600 !important;
  border-radius: 10px !important;
  height: 50px !important;
  transition: all 0.15s ease !important;
  letter-spacing: -0.01em !important;
}
[data-testid="stButton"] > button[kind="primary"] {
  background: #16a34a !important;
  border: none !important;
  color: #fff !important;
  box-shadow: 0 1px 2px rgba(22,163,74,0.2) !important;
}
[data-testid="stButton"] > button[kind="primary"]:hover {
  background: #15803d !important;
  box-shadow: 0 4px 12px rgba(22,163,74,0.3) !important;
  transform: translateY(-1px) !important;
}
[data-testid="stButton"] > button[kind="secondary"] {
  background: #fff !important;
  border: 1.5px solid #e8e6e0 !important;
  color: #374151 !important;
}
[data-testid="stButton"] > button[kind="secondary"]:hover {
  border-color: #9ca3af !important;
  background: #f9fafb !important;
}

/* ── Score display ── */
.score-hero {
  text-align: center;
  padding: 24px 0 32px;
}
.score-number {
  font-size: 80px;
  font-weight: 800;
  letter-spacing: -0.05em;
  line-height: 1;
}
.score-denom {
  font-size: 24px;
  font-weight: 400;
  color: #9ca3af;
  margin-left: 4px;
}
.score-label {
  font-size: 18px;
  font-weight: 600;
  margin-top: 8px;
  letter-spacing: -0.02em;
}

/* ── Metric pills ── */
.metric-row {
  display: flex;
  gap: 12px;
  margin: 24px 0;
}
.metric-pill {
  flex: 1;
  background: #fafaf9;
  border: 1px solid #e8e6e0;
  border-radius: 12px;
  padding: 16px;
  text-align: center;
}
.metric-pill-label {
  font-family: 'DM Mono', monospace;
  font-size: 10px;
  font-weight: 500;
  color: #9ca3af;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  margin-bottom: 6px;
}
.metric-pill-value {
  font-size: 22px;
  font-weight: 700;
  color: #1a1a1a;
  letter-spacing: -0.03em;
}
.metric-pill-bar {
  height: 3px;
  background: #f0ede6;
  border-radius: 99px;
  margin-top: 10px;
  overflow: hidden;
}
.metric-pill-fill {
  height: 100%;
  background: #16a34a;
  border-radius: 99px;
}

/* ── Section heading ── */
.section-heading {
  font-size: 13px;
  font-weight: 700;
  color: #1a1a1a;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 14px;
  margin-top: 4px;
}

/* ── Skill tags ── */
.tags { display: flex; flex-wrap: wrap; gap: 6px; }
.tag {
  padding: 4px 12px;
  border-radius: 99px;
  font-size: 12px;
  font-weight: 500;
  line-height: 1.8;
}
.tag-green { background: #dcfce7; color: #15803d; }
.tag-red   { background: #fee2e2; color: #b91c1c; }
.tag-blue  { background: #dbeafe; color: #1d4ed8; }

/* ── Info rows ── */
.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 11px 0;
  border-bottom: 1px solid #f0ede6;
  font-size: 14px;
}
.info-row:last-child { border-bottom: none; }
.info-key { color: #9ca3af; font-weight: 400; }
.info-val { color: #1a1a1a; font-weight: 600; }

/* ── Recommendation card ── */
.rec-card {
  display: flex;
  gap: 14px;
  align-items: flex-start;
  padding: 14px 16px;
  background: #fafaf9;
  border: 1px solid #e8e6e0;
  border-left: 4px solid #16a34a;
  border-radius: 0 10px 10px 0;
  margin-bottom: 10px;
  font-size: 14px;
  color: #374151;
  line-height: 1.6;
}
.rec-num {
  width: 22px; height: 22px;
  min-width: 22px;
  background: #16a34a;
  color: #fff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  margin-top: 1px;
}

/* ── Success banner ── */
.success-banner {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 10px;
  padding: 14px 18px;
  font-size: 14px;
  color: #15803d;
  font-weight: 500;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 10px;
}

/* ── Error banner ── */
.error-banner {
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 10px;
  padding: 14px 18px;
  font-size: 14px;
  color: #b91c1c;
  font-weight: 500;
  margin-bottom: 12px;
}

/* ── Download button ── */
[data-testid="stDownloadButton"] > button {
  font-family: 'DM Sans', sans-serif !important;
  font-size: 15px !important;
  font-weight: 600 !important;
  border-radius: 10px !important;
  height: 50px !important;
  background: #fff !important;
  border: 1.5px solid #e8e6e0 !important;
  color: #374151 !important;
  width: 100% !important;
}
[data-testid="stDownloadButton"] > button:hover {
  border-color: #16a34a !important;
  color: #16a34a !important;
}

/* ── Mobile ── */
@media (max-width: 640px) {
  .card { padding: 32px 20px; margin: 0 12px 24px; }
  .step-title { font-size: 22px; }
  .score-number { font-size: 64px; }
  .metric-row { gap: 8px; }
  .topbar { padding: 0 16px; }
}
</style>
""", unsafe_allow_html=True)


# ── Helper — render top bar ─────────────────────────────────────────────────
def render_topbar(current_step: int):
    pills_html = ""
    for i in range(1, 5):
        if i < current_step:
            cls, content = "pill-done", "✓"
        elif i == current_step:
            cls, content = "pill-active", str(i)
        else:
            cls, content = "pill-todo", str(i)
        pills_html += f'<div class="pill {cls}">{content}</div>'
        if i < 4:
            pills_html += '<div class="pill-connector"></div>'

    st.markdown(f"""
    <div class="topbar">
      <div class="topbar-brand"><span>📄</span>Resume Analyzer</div>
      <div class="step-pills">{pills_html}</div>
    </div>
    """, unsafe_allow_html=True)


def score_color(score: float) -> str:
    if score >= 75: return "#16a34a"
    if score >= 55: return "#3b82f6"
    if score >= 35: return "#f59e0b"
    return "#ef4444"


# ==============================================================================
# STEP 1 — Candidate Details
# ==============================================================================
if st.session_state.step == 1:
    render_topbar(1)

    st.markdown("""
    <div class="card">
      <div class="step-label">Step 1 of 4</div>
      <div class="step-title">Tell us about the candidate</div>
      <div class="step-sub">This information will appear on the generated report and email.</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div style="max-width:620px;margin:0 auto;">', unsafe_allow_html=True)

    name  = st.text_input("Full name",        value=st.session_state.candidate_name,  placeholder="e.g. Izaan Kazmi")
    email = st.text_input("Email address",    value=st.session_state.candidate_email, placeholder="e.g. izaan@example.com")
    role  = st.text_input("Role applying for",value=st.session_state.job_title,       placeholder="e.g. Senior Software Engineer")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    if st.button("Continue →", type="primary", use_container_width=True):
        errors = []
        if not name.strip():          errors.append("Please enter the candidate's full name.")
        if not email.strip():         errors.append("Please enter the candidate's email address.")
        if "@" not in email:          errors.append("Please enter a valid email address.")
        if not role.strip():          errors.append("Please enter the role being applied for.")

        if errors:
            for e in errors:
                st.markdown(f'<div class="error-banner">⚠ {e}</div>', unsafe_allow_html=True)
        else:
            st.session_state.candidate_name  = name
            st.session_state.candidate_email = email
            st.session_state.job_title       = role
            st.session_state.step            = 2
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


# ==============================================================================
# STEP 2 — Upload Resume
# ==============================================================================
elif st.session_state.step == 2:
    render_topbar(2)

    st.markdown("""
    <div class="card">
      <div class="step-label">Step 2 of 4</div>
      <div class="step-title">Upload the resume</div>
      <div class="step-sub">Supported formats: PDF and DOCX. Maximum file size 10 MB.</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div style="max-width:620px;margin:0 auto;">', unsafe_allow_html=True)

    uploaded = st.file_uploader("Drag and drop or click to browse", type=["pdf", "docx"])

    if uploaded:
        st.markdown(
            f'<div class="success-banner">✓ &nbsp;<strong>{uploaded.name}</strong> uploaded successfully</div>',
            unsafe_allow_html=True,
        )
        st.session_state.resume_file = uploaded

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    col_back, col_next = st.columns([1, 2])
    with col_back:
        if st.button("← Back", type="secondary", use_container_width=True):
            st.session_state.step = 1
            st.rerun()
    with col_next:
        if st.button("Continue →", type="primary", use_container_width=True):
            if not st.session_state.resume_file:
                st.markdown('<div class="error-banner">⚠ Please upload a resume file before continuing.</div>', unsafe_allow_html=True)
            else:
                st.session_state.step = 3
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


# ==============================================================================
# STEP 3 — Job Description
# ==============================================================================
elif st.session_state.step == 3:
    render_topbar(3)

    st.markdown("""
    <div class="card">
      <div class="step-label">Step 3 of 4</div>
      <div class="step-title">Paste the job description</div>
      <div class="step-sub">Copy the full job posting including requirements and responsibilities for the most accurate analysis.</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div style="max-width:620px;margin:0 auto;">', unsafe_allow_html=True)

    jd = st.text_area(
        "Job description",
        value=st.session_state.jd_text,
        height=260,
        placeholder="We are looking for a Software Engineer with experience in Python, REST APIs, Docker, AWS...\n\nRequirements:\n- 3+ years of experience\n- Strong Python skills\n- ..."
    )

    st.markdown(
        f'<div style="text-align:right;font-size:12px;color:#9ca3af;margin-top:4px;">{len(jd)} characters</div>',
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    col_back, col_next = st.columns([1, 2])
    with col_back:
        if st.button("← Back", type="secondary", use_container_width=True):
            st.session_state.step = 2
            st.rerun()
    with col_next:
        if st.button("Analyse Resume →", type="primary", use_container_width=True):
            if not jd.strip():
                st.markdown('<div class="error-banner">⚠ Please paste the job description before continuing.</div>', unsafe_allow_html=True)
            elif len(jd.strip()) < 50:
                st.markdown('<div class="error-banner">⚠ The job description seems too short. Please paste the full posting.</div>', unsafe_allow_html=True)
            else:
                st.session_state.jd_text = jd
                st.session_state.step    = 4
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


# ==============================================================================
# STEP 4 — Results
# ==============================================================================
elif st.session_state.step == 4:
    render_topbar(4)

    # ── Run analysis if not already done ──
    if st.session_state.results is None:
        with st.spinner("Analysing resume — this may take 20–30 seconds…"):
            try:
                resume_file = st.session_state.resume_file
                suffix = ".pdf" if resume_file.name.endswith(".pdf") else ".docx"

                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(resume_file.read())
                    tmp_path = tmp.name

                resume_text       = parse_resume(tmp_path)
                skills_result     = extract_skills(resume_text)
                experience_result = extract_experience(resume_text)
                education_result  = extract_education(resume_text)

                match_result = match_resume_to_jd(
                    resume_text      = resume_text,
                    jd_text          = st.session_state.jd_text,
                    experience_level = experience_result.get("experience_level"),
                )

                html_report = generate_report(
                    candidate_name    = st.session_state.candidate_name,
                    candidate_email   = st.session_state.candidate_email,
                    skills_result     = skills_result,
                    experience_result = experience_result,
                    education_result  = education_result,
                    match_result      = match_result,
                    job_title         = st.session_state.job_title,
                )

                os.unlink(tmp_path)

                st.session_state.results     = {
                    "skills":     skills_result,
                    "experience": experience_result,
                    "education":  education_result,
                    "match":      match_result,
                }
                st.session_state.html_report = html_report

            except Exception as e:
                st.markdown(f'<div class="error-banner">⚠ Analysis failed: {str(e)}</div>', unsafe_allow_html=True)
                if st.button("← Try again", type="secondary"):
                    st.session_state.step    = 1
                    st.session_state.results = None
                    st.rerun()
                st.stop()

        st.rerun()

    # ── Display results ──
    r     = st.session_state.results
    match = r["match"]
    exp   = r["experience"]
    edu   = r["education"]
    score = match["composite_score"]
    color = score_color(score)

    st.markdown('<div style="max-width:620px;margin:0 auto;">', unsafe_allow_html=True)

    # Score hero
    st.markdown(f"""
    <div class="card" style="text-align:center;padding:40px 48px;">
      <div class="step-label">Analysis complete</div>
      <div class="score-hero">
        <div class="score-number" style="color:{color};">{score:.0f}<span class="score-denom">/100</span></div>
        <div class="score-label" style="color:{color};">{match['match_label']}</div>
      </div>
      <div class="metric-row">
        <div class="metric-pill">
          <div class="metric-pill-label">Keyword</div>
          <div class="metric-pill-value">{match['tfidf_score']:.0f}%</div>
          <div class="metric-pill-bar"><div class="metric-pill-fill" style="width:{match['tfidf_score']}%"></div></div>
        </div>
        <div class="metric-pill">
          <div class="metric-pill-label">Semantic</div>
          <div class="metric-pill-value">{match['semantic_score']:.0f}%</div>
          <div class="metric-pill-bar"><div class="metric-pill-fill" style="width:{match['semantic_score']}%"></div></div>
        </div>
        <div class="metric-pill">
          <div class="metric-pill-label">Skills</div>
          <div class="metric-pill-value">{match['skills_score']:.0f}%</div>
          <div class="metric-pill-bar"><div class="metric-pill-fill" style="width:{match['skills_score']}%"></div></div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Skills tabs
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-heading">Skills Analysis</div>', unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs([
        f"✅  Matched  {len(match['matched_skills'])}",
        f"❌  Missing  {len(match['missing_skills'])}",
        f"➕  Extra  {len(match['extra_skills'])}",
    ])
    with tab1:
        if match["matched_skills"]:
            tags = " ".join(f'<span class="tag tag-green">{s}</span>' for s in match["matched_skills"])
            st.markdown(f'<div class="tags" style="margin-top:12px;">{tags}</div>', unsafe_allow_html=True)
        else:
            st.caption("No matched skills found.")
    with tab2:
        if match["missing_skills"]:
            tags = " ".join(f'<span class="tag tag-red">{s}</span>' for s in match["missing_skills"])
            st.markdown(f'<div class="tags" style="margin-top:12px;">{tags}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="success-banner" style="margin-top:12px;">✓ No missing skills — excellent match!</div>', unsafe_allow_html=True)
    with tab3:
        if match["extra_skills"]:
            tags = " ".join(f'<span class="tag tag-blue">{s}</span>' for s in match["extra_skills"])
            st.markdown(f'<div class="tags" style="margin-top:12px;">{tags}</div>', unsafe_allow_html=True)
        else:
            st.caption("No extra skills detected.")

    st.markdown('</div>', unsafe_allow_html=True)

    # Experience + Education
    col_exp, col_edu = st.columns(2)

    with col_exp:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-heading">Experience</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="info-row"><span class="info-key">Total</span><span class="info-val">{exp['total_experience']} years</span></div>
        <div class="info-row"><span class="info-key">Level</span><span class="info-val">{exp['experience_level']}</span></div>
        """, unsafe_allow_html=True)
        for entry in exp.get("job_titles", [])[:3]:
            t = entry.get("title", "")[:38]
            st.markdown(f'<div class="info-row"><span class="info-val" style="font-size:13px;">{t}</span></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_edu:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-heading">Education</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="info-row"><span class="info-key">Highest</span><span class="info-val">{edu.get('highest_degree') or 'N/A'}</span></div>
        """, unsafe_allow_html=True)
        for entry in edu.get("education_entries", [])[:3]:
            line = " · ".join(filter(None, [
                entry.get("degree") or "",
                entry.get("field")  or "",
                str(entry.get("year")) if entry.get("year") else ""
            ]))
            st.markdown(f'<div class="info-row"><span class="info-val" style="font-size:13px;">{line}</span></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Recommendations
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-heading">Recommendations</div>', unsafe_allow_html=True)
    for i, rec in enumerate(match.get("recommendations", []), 1):
        st.markdown(f'<div class="rec-card"><div class="rec-num">{i}</div><div>{rec}</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Actions
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-heading">Actions</div>', unsafe_allow_html=True)

    st.download_button(
        label="⬇  Download HTML Report",
        data=st.session_state.html_report,
        file_name=f"resume_report_{st.session_state.candidate_name.replace(' ', '_')}.html",
        mime="text/html",
        use_container_width=True,
    )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    if st.button("✉  Send Report by Email", type="primary", use_container_width=True):
        with st.spinner(f"Sending to {st.session_state.candidate_email}…"):
            result = send_report_email(
                recipient_email=st.session_state.candidate_email,
                recipient_name=st.session_state.candidate_name,
                html_report=st.session_state.html_report,
                job_title=st.session_state.job_title,
                method="smtp",
            )
        if result["success"]:
            st.markdown(f'<div class="success-banner">✓ Report sent to <strong>{st.session_state.candidate_email}</strong></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="error-banner">⚠ Email failed: {result["error"]}</div>', unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    if st.button("← Analyse another resume", type="secondary", use_container_width=True):
        for key in ["step","candidate_name","candidate_email","job_title",
                    "resume_file","jd_text","results","html_report","email_sent"]:
            del st.session_state[key]
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
