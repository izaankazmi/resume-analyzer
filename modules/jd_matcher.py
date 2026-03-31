import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# =============================================================================
# jd_matcher.py
# =============================================================================
# Responsibility : Compare a resume against a job description.
#                 Produces a match score, identifies skill gaps,
#                 and highlights matching strengths.
# Used by       : main.py, report_generator.py
# Dependencies  : scikit-learn, sentence-transformers, skills_extractor.py
# =============================================================================

import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from modules.skills_extractor import extract_skills


# -----------------------------------------------------------------------------
# Load sentence transformer model once at module level
# -----------------------------------------------------------------------------

try:
    SEMANTIC_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
except Exception as e:
    raise RuntimeError(
        f"Could not load SentenceTransformer model.\n"
        f"Reason: {e}\n"
        f"Make sure sentence-transformers is installed correctly."
    )


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# Weight distribution for the final composite score
TFIDF_WEIGHT    = 0.35   # keyword overlap score
SEMANTIC_WEIGHT = 0.45   # meaning-level similarity score
SKILLS_WEIGHT   = 0.20   # skills overlap score

# Score thresholds for match label
SCORE_EXCELLENT = 75
SCORE_GOOD      = 55
SCORE_FAIR      = 35


# -----------------------------------------------------------------------------
# Internal helpers
# -----------------------------------------------------------------------------

def _clean_text_for_matching(text: str) -> str:
    """
    Lightweight cleaning before vectorisation.
    Lowercases, removes punctuation, collapses whitespace.
    Keeps numbers as they may be meaningful (e.g. Python 3, AWS S3).
    """
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)   # remove punctuation
    text = re.sub(r"\s+", " ", text)        # collapse whitespace
    return text.strip()


def _tfidf_score(resume_text: str, jd_text: str) -> float:
    """
    Compute TF-IDF cosine similarity between resume and job description.
    Returns a score between 0.0 and 100.0.
    TF-IDF captures keyword overlap — good for exact term matching.
    """
    cleaned_resume = _clean_text_for_matching(resume_text)
    cleaned_jd     = _clean_text_for_matching(jd_text)

    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),    # unigrams and bigrams
        stop_words="english",  # remove common English stopwords
        min_df=1,
    )

    try:
        tfidf_matrix = vectorizer.fit_transform([cleaned_resume, cleaned_jd])
        score = cosine_similarity(tfidf_matrix[0], tfidf_matrix[1])[0][0]
        return round(float(score) * 100, 2)
    except ValueError:
        # Happens if one of the texts is empty after cleaning
        return 0.0


def _semantic_score(resume_text: str, jd_text: str) -> float:
    """
    Compute semantic similarity using sentence-transformers.
    Returns a score between 0.0 and 100.0.
    Semantic scoring captures meaning-level similarity —
    e.g. 'built REST APIs' matches 'developed web services'
    even without shared keywords.
    """
    try:
        embeddings = SEMANTIC_MODEL.encode(
            [resume_text, jd_text],
            convert_to_tensor=False,
            show_progress_bar=False,
        )
        score = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
        return round(float(score) * 100, 2)
    except Exception:
        return 0.0


def _skills_overlap_score(
    resume_skills: list,
    jd_skills: list,
) -> tuple:
    """
    Compare skills extracted from the resume vs the job description.
    Returns:
        - score         : float 0-100 based on % of JD skills matched
        - matched       : list of skills present in both
        - missing       : list of skills in JD but not in resume
        - extra         : list of skills in resume but not in JD
    """
    resume_set = set(s.lower() for s in resume_skills)
    jd_set     = set(s.lower() for s in jd_skills)

    matched = sorted(resume_set & jd_set)
    missing = sorted(jd_set - resume_set)
    extra   = sorted(resume_set - jd_set)

    if not jd_set:
        score = 0.0
    else:
        score = round((len(matched) / len(jd_set)) * 100, 2)

    return score, matched, missing, extra


def _generate_recommendations(
    missing_skills: list,
    match_score: float,
    experience_level: str | None,
) -> list:
    """
    Generate a list of actionable improvement recommendations
    based on skill gaps and overall match score.
    Returns a list of recommendation strings.
    """
    recommendations = []

    # Skill gap recommendations
    if missing_skills:
        top_missing = missing_skills[:5]  # focus on top 5 gaps
        recommendations.append(
            f"Develop or highlight these missing skills: "
            f"{', '.join(top_missing)}."
        )

    if len(missing_skills) > 5:
        recommendations.append(
            f"You are missing {len(missing_skills)} skills mentioned in the "
            f"job description. Consider upskilling or adding relevant "
            f"projects to your resume to bridge these gaps."
        )

    # Score-based recommendations
    if match_score < SCORE_FAIR:
        recommendations.append(
            "Your resume has a low overall match with this job description. "
            "Consider tailoring your resume language to more closely reflect "
            "the terminology used in the job posting."
        )
    elif match_score < SCORE_GOOD:
        recommendations.append(
            "Your resume partially matches this role. Strengthen the match "
            "by adding more specific achievements and keywords from the "
            "job description."
        )
    elif match_score < SCORE_EXCELLENT:
        recommendations.append(
            "Good match overall. Fine-tune your resume by quantifying "
            "achievements (e.g. 'improved performance by 30%') to stand out."
        )
    else:
        recommendations.append(
            "Excellent match. Make sure your resume is well-formatted "
            "and your most relevant experience appears near the top."
        )

    # Experience level recommendations
    if experience_level == "Entry":
        recommendations.append(
            "As an entry-level candidate, highlight academic projects, "
            "internships, and personal projects to demonstrate practical skills."
        )
    elif experience_level == "Mid":
        recommendations.append(
            "Emphasise measurable impact in your previous roles — "
            "use numbers and outcomes wherever possible."
        )
    elif experience_level == "Senior":
        recommendations.append(
            "Highlight leadership, mentoring, and architectural decisions "
            "in addition to technical skills."
        )

    return recommendations


def _score_label(score: float) -> str:
    """
    Convert a numeric score to a human-readable match label.
    """
    if score >= SCORE_EXCELLENT:
        return "Excellent Match"
    elif score >= SCORE_GOOD:
        return "Good Match"
    elif score >= SCORE_FAIR:
        return "Fair Match"
    else:
        return "Low Match"


# -----------------------------------------------------------------------------
# Public interface
# -----------------------------------------------------------------------------

def match_resume_to_jd(
    resume_text: str,
    jd_text: str,
    skills_file_path: str = "data/skills_list.txt",
    experience_level: str | None = None,
) -> dict:
    """
    Main entry point. Compares a resume against a job description and
    returns a comprehensive match report.

    Parameters
    ----------
    resume_text : str
        Plain text of the resume (from file_parser.parse_resume).
    jd_text : str
        Plain text of the job description (pasted by user).
    skills_file_path : str
        Path to curated skills list. Defaults to data/skills_list.txt.
    experience_level : str or None
        Optional experience level from experience_extractor
        ('Entry', 'Mid', 'Senior', 'Executive').
        Used to tailor recommendations.

    Returns
    -------
    dict with keys:
        - tfidf_score         : float — keyword overlap score (0-100)
        - semantic_score      : float — meaning-level similarity (0-100)
        - skills_score        : float — skills overlap score (0-100)
        - composite_score     : float — weighted final score (0-100)
        - match_label         : str   — 'Excellent', 'Good', 'Fair', 'Low'
        - matched_skills      : list  — skills in both resume and JD
        - missing_skills      : list  — skills in JD but not in resume
        - extra_skills        : list  — skills in resume but not required
        - recommendations     : list  — actionable improvement suggestions
        - score_breakdown     : dict  — individual scores with weights

    Raises
    ------
    ValueError
        If resume_text or jd_text is empty.
    """

    # 1. Validate inputs
    if not resume_text or not resume_text.strip():
        raise ValueError("Resume text is empty.")

    if not jd_text or not jd_text.strip():
        raise ValueError(
            "Job description is empty. Please paste the job description."
        )

    # 2. Extract skills from both resume and job description
    resume_skills_result = extract_skills(
        resume_text,
        skills_file_path=skills_file_path,
    )
    jd_skills_result = extract_skills(
        jd_text,
        skills_file_path=skills_file_path,
    )

    resume_skills = resume_skills_result["all_skills"]
    jd_skills     = jd_skills_result["all_skills"]

    # 3. Compute individual scores
    tfidf_score    = _tfidf_score(resume_text, jd_text)
    semantic_score = _semantic_score(resume_text, jd_text)
    skills_score, matched_skills, missing_skills, extra_skills = (
        _skills_overlap_score(resume_skills, jd_skills)
    )

    # 4. Compute composite weighted score
    composite_score = round(
        (tfidf_score    * TFIDF_WEIGHT)
        + (semantic_score * SEMANTIC_WEIGHT)
        + (skills_score   * SKILLS_WEIGHT),
        2,
    )

    # 5. Generate match label
    label = _score_label(composite_score)

    # 6. Generate recommendations
    recommendations = _generate_recommendations(
        missing_skills,
        composite_score,
        experience_level,
    )

    return {
        "tfidf_score":     tfidf_score,
        "semantic_score":  semantic_score,
        "skills_score":    skills_score,
        "composite_score": composite_score,
        "match_label":     label,
        "matched_skills":  matched_skills,
        "missing_skills":  missing_skills,
        "extra_skills":    extra_skills,
        "recommendations": recommendations,
        "score_breakdown": {
            "tfidf":    {"score": tfidf_score,    "weight": TFIDF_WEIGHT},
            "semantic": {"score": semantic_score, "weight": SEMANTIC_WEIGHT},
            "skills":   {"score": skills_score,   "weight": SKILLS_WEIGHT},
        },
    }


# -----------------------------------------------------------------------------
# Quick manual test
# python modules/jd_matcher.py
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    sample_resume = """
    John Doe — Senior Software Engineer

    Skills: Python, Django, REST APIs, PostgreSQL, Docker,
    Git, AWS, React, JavaScript, CI/CD, Agile

    Experience:
    Senior Software Engineer — TechCorp (2021 - Present)
    Developed microservices using Python and FastAPI.
    Deployed applications on AWS using Docker and Kubernetes.

    Software Developer — StartupXYZ (2018 - 2020)
    Built REST APIs with Django and PostgreSQL.
    Worked on CI/CD pipelines using GitHub Actions.

    Education:
    B.Sc. Computer Science, University of Karachi, 2018
    """

    sample_jd = """
    We are looking for a Software Engineer with:
    - Strong experience in Python and Django
    - Knowledge of REST APIs and microservices
    - Experience with AWS and Docker
    - Familiarity with PostgreSQL and Redis
    - Experience with React or any modern frontend framework
    - Understanding of CI/CD pipelines
    - Knowledge of Kubernetes is a plus
    - Good communication and teamwork skills
    - Agile development experience
    """

    print("\nRunning JD matching on sample data...")
    print("-" * 60)

    try:
        result = match_resume_to_jd(
            sample_resume,
            sample_jd,
            experience_level="Senior",
        )

        print(f"Match label      : {result['match_label']}")
        print(f"Composite score  : {result['composite_score']}%")
        print(f"\nScore breakdown:")
        print(f"  TF-IDF score   : {result['tfidf_score']}%"
              f" (weight {TFIDF_WEIGHT})")
        print(f"  Semantic score : {result['semantic_score']}%"
              f" (weight {SEMANTIC_WEIGHT})")
        print(f"  Skills score   : {result['skills_score']}%"
              f" (weight {SKILLS_WEIGHT})")

        print(f"\nMatched skills ({len(result['matched_skills'])}):")
        for s in result["matched_skills"]:
            print(f"  + {s}")

        print(f"\nMissing skills ({len(result['missing_skills'])}):")
        for s in result["missing_skills"]:
            print(f"  - {s}")

        print(f"\nExtra skills on resume ({len(result['extra_skills'])}):")
        for s in result["extra_skills"]:
            print(f"  ~ {s}")

        print(f"\nRecommendations:")
        for i, rec in enumerate(result["recommendations"], 1):
            print(f"  {i}. {rec}")

    except (ValueError, FileNotFoundError) as e:
        print(f"Error: {e}")
        sys.exit(1)