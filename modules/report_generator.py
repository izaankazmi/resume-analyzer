import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# =============================================================================
# report_generator.py
# =============================================================================
# Responsibility : Take all extracted data and match results and render
#                 a clean, structured HTML feedback report using Jinja2.
# Used by       : main.py, email_agent.py
# Dependencies  : Jinja2
# =============================================================================

from datetime import datetime
from jinja2 import Environment, FileSystemLoader, select_autoescape


# -----------------------------------------------------------------------------
# Internal helpers
# -----------------------------------------------------------------------------

def _get_score_color(score: float) -> str:
    """
    Return a hex color based on the score value.
    Used in the report to visually indicate match quality.
    """
    if score >= 75:
        return "#2ecc71"   # green  — excellent
    elif score >= 55:
        return "#3498db"   # blue   — good
    elif score >= 35:
        return "#f39c12"   # orange — fair
    else:
        return "#e74c3c"   # red    — low


def _format_education_entries(education_entries: list) -> list:
    """
    Format education entries for clean display in the report.
    Fills in 'Not detected' for any missing fields.
    """
    formatted = []
    for entry in education_entries:
        formatted.append({
            "degree":      entry.get("degree")      or "Not detected",
            "field":       entry.get("field")        or "Not detected",
            "institution": entry.get("institution")  or "Not detected",
            "year":        entry.get("year")         or "Not detected",
        })
    return formatted


def _format_job_titles(job_titles: list) -> list:
    """
    Format job title entries for display in the report.
    """
    formatted = []
    for entry in job_titles:
        formatted.append({
            "title":   entry.get("title")   or "Not detected",
            "company": entry.get("company") or "Not detected",
        })
    return formatted[:5]  # show max 5 most recent roles


# -----------------------------------------------------------------------------
# Public interface
# -----------------------------------------------------------------------------

def generate_report(
    candidate_name: str,
    candidate_email: str,
    skills_result: dict,
    experience_result: dict,
    education_result: dict,
    match_result: dict,
    job_title: str = "the position",
    template_dir: str = "templates",
    template_file: str = "report_template.html",
) -> str:
    """
    Main entry point. Renders a full HTML feedback report using Jinja2.

    Parameters
    ----------
    candidate_name  : str  — candidate's full name
    candidate_email : str  — candidate's email address
    skills_result   : dict — output of skills_extractor.extract_skills()
    experience_result: dict — output of experience_extractor.extract_experience()
    education_result : dict — output of education_extractor.extract_education()
    match_result    : dict — output of jd_matcher.match_resume_to_jd()
    job_title       : str  — name of the role being applied for
    template_dir    : str  — folder containing the Jinja2 template
    template_file   : str  — name of the HTML template file

    Returns
    -------
    str
        Fully rendered HTML report as a string.
        Ready to display in Streamlit or send via email.

    Raises
    ------
    FileNotFoundError
        If the template file does not exist.
    ValueError
        If required result dicts are missing or empty.
    """

    # 1. Validate inputs
    if not candidate_name or not candidate_name.strip():
        candidate_name = "Candidate"

    if not candidate_email or not candidate_email.strip():
        candidate_email = "Not provided"

    if not match_result:
        raise ValueError("Match result is empty. Run jd_matcher first.")

    # 2. Check template exists
    template_path = os.path.join(template_dir, template_file)
    if not os.path.exists(template_path):
        raise FileNotFoundError(
            f"Template not found at: {template_path}\n"
            f"Please create templates/report_template.html"
        )

    # 3. Set up Jinja2 environment
    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(["html"]),
    )

    template = env.get_template(template_file)

    # 4. Build the template context — all data the template needs
    composite_score = match_result.get("composite_score", 0)

    context = {
        # Candidate info
        "candidate_name":   candidate_name,
        "candidate_email":  candidate_email,
        "job_title":        job_title,
        "report_date":      datetime.now().strftime("%B %d, %Y"),

        # Match scores
        "composite_score":  composite_score,
        "score_color":      _get_score_color(composite_score),
        "match_label":      match_result.get("match_label", "N/A"),
        "tfidf_score":      match_result.get("tfidf_score", 0),
        "semantic_score":   match_result.get("semantic_score", 0),
        "skills_score":     match_result.get("skills_score", 0),

        # Skills
        "matched_skills":   match_result.get("matched_skills", []),
        "missing_skills":   match_result.get("missing_skills", []),
        "extra_skills":     match_result.get("extra_skills", []),
        "all_skills":       skills_result.get("all_skills", []),
        "total_skills":     skills_result.get("total_count", 0),

        # Experience
        "job_titles":         _format_job_titles(
                                experience_result.get("job_titles", [])
                              ),
        "total_experience":   experience_result.get("total_experience", 0),
        "experience_level":   experience_result.get("experience_level", "N/A"),
        "date_ranges":        experience_result.get("date_ranges", []),

        # Education
        "education_entries":  _format_education_entries(
                                education_result.get("education_entries", [])
                              ),
        "highest_degree":     education_result.get("highest_degree", "N/A"),

        # Recommendations
        "recommendations":    match_result.get("recommendations", []),
    }

    # 5. Render the template
    rendered_html = template.render(**context)

    return rendered_html


def save_report(html_content: str, output_path: str = "report.html") -> str:
    """
    Save the rendered HTML report to a file on disk.
    Useful for debugging or downloading the report.

    Parameters
    ----------
    html_content : str — the rendered HTML string
    output_path  : str — where to save the file

    Returns
    -------
    str — the absolute path where the file was saved
    """
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return os.path.abspath(output_path)


# -----------------------------------------------------------------------------
# Quick manual test
# python modules/report_generator.py
# -----------------------------------------------------------------------------

if __name__ == "__main__":

    # Sample data mimicking real module outputs
    sample_skills = {
        "matched_skills": ["python", "django", "docker", "aws", "postgresql"],
        "ner_skills":     ["techcorp", "startupxyz"],
        "all_skills":     ["agile", "aws", "ci/cd", "django", "docker",
                           "git", "javascript", "postgresql", "python",
                           "react", "rest api"],
        "total_count":    11,
    }

    sample_experience = {
        "job_titles": [
            {"title": "Senior Software Engineer — TechCorp", "company": "TechCorp"},
            {"title": "Software Developer — StartupXYZ",     "company": "StartupXYZ"},
        ],
        "date_ranges": [
            {"raw": "2021 - Present", "start_year": 2021,
             "end_year": 2026, "duration_years": 5},
            {"raw": "2018 - 2020",    "start_year": 2018,
             "end_year": 2020, "duration_years": 2},
        ],
        "total_experience": 8.0,
        "experience_level": "Senior",
    }

    sample_education = {
        "education_entries": [
            {"degree": "Bachelors", "field": "Computer Science",
             "institution": "University of Karachi", "year": 2018},
        ],
        "highest_degree": "Bachelors",
        "total_entries":  1,
    }

    sample_match = {
        "tfidf_score":     62.5,
        "semantic_score":  71.3,
        "skills_score":    80.0,
        "composite_score": 69.8,
        "match_label":     "Good Match",
        "matched_skills":  ["python", "django", "docker", "aws"],
        "missing_skills":  ["redis", "kubernetes"],
        "extra_skills":    ["react", "javascript"],
        "recommendations": [
            "Develop or highlight these missing skills: redis, kubernetes.",
            "Good match overall. Quantify your achievements.",
            "Highlight leadership and mentoring experience.",
        ],
        "score_breakdown": {
            "tfidf":    {"score": 62.5, "weight": 0.35},
            "semantic": {"score": 71.3, "weight": 0.45},
            "skills":   {"score": 80.0, "weight": 0.20},
        },
    }

    print("\nGenerating sample report...")
    print("-" * 60)

    try:
        html = generate_report(
            candidate_name    = "John Doe",
            candidate_email   = "john.doe@example.com",
            skills_result     = sample_skills,
            experience_result = sample_experience,
            education_result  = sample_education,
            match_result      = sample_match,
            job_title         = "Senior Software Engineer",
        )

        path = save_report(html, output_path="report.html")
        print(f"Report generated successfully.")
        print(f"Saved to: {path}")
        print(f"Total HTML length: {len(html)} characters")

    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}")
        sys.exit(1)