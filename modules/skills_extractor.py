# =============================================================================
# skills_extractor.py
# =============================================================================
# Responsibility : Extract skills from resume plain text.
# Used by       : main.py, jd_matcher.py
# Dependencies  : spaCy, a curated skills_list.txt in the data/ folder
# =============================================================================

import os
import re
import spacy


# -----------------------------------------------------------------------------
# Load spaCy model once at module level (avoids reloading on every call)
# -----------------------------------------------------------------------------

try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    raise OSError(
        "spaCy model not found. Please run:\n"
        "python -m spacy download en_core_web_sm"
    )


# -----------------------------------------------------------------------------
# Internal helpers
# -----------------------------------------------------------------------------

def _load_skills_list(skills_file_path: str) -> set:
    """
    Load the curated skills list from a plain text file.
    Each line in the file is one skill (case-insensitive).
    Returns a set of lowercase skill strings.
    """
    if not os.path.exists(skills_file_path):
        raise FileNotFoundError(
            f"Skills list not found at: {skills_file_path}\n"
            f"Please create data/skills_list.txt with one skill per line."
        )

    with open(skills_file_path, "r", encoding="utf-8") as f:
        skills = set()
        for line in f:
            skill = line.strip().lower()
            if skill and not skill.startswith("#"):  # skip empty lines and comments
                skills.add(skill)

    return skills


def _extract_by_keyword_match(text: str, skills_list: set) -> set:
    """
    Match skills from the curated list against the resume text.
    Uses whole-word matching to avoid false positives
    e.g. 'R' should not match inside 'React' or 'Rust'.
    Returns a set of matched skill strings.
    """
    text_lower = text.lower()
    matched = set()

    for skill in skills_list:
        # Escape special regex characters in skill names (e.g. C++, .NET)
        escaped = re.escape(skill)
        # Use word boundary for single words, flexible for multi-word skills
        pattern = rf"\b{escaped}\b"
        if re.search(pattern, text_lower):
            matched.add(skill)

    return matched


def _extract_by_ner(text: str) -> set:
    """
    Use spaCy Named Entity Recognition to find additional skill-like terms.
    Looks for ORG and PRODUCT entities which often capture tech names,
    frameworks, and tools that may not be in the curated list.
    Returns a set of extracted strings.
    """
    doc = nlp(text)
    ner_skills = set()

    for ent in doc.ents:
        if ent.label_ in ("ORG", "PRODUCT"):
            cleaned = ent.text.strip().lower()
            if len(cleaned) > 1:           # skip single characters
                ner_skills.add(cleaned)

    return ner_skills


def _clean_skills(skills: set) -> list:
    """
    Final cleanup of the extracted skills set:
    - Remove duplicates (already handled by set)
    - Remove skills that are just numbers or single characters
    - Sort alphabetically for consistent output
    Returns a sorted list of clean skill strings.
    """
    cleaned = set()

    for skill in skills:
        skill = skill.strip()
        if len(skill) < 2:                 # skip single characters
            continue
        if skill.isdigit():                # skip pure numbers
            continue
        cleaned.add(skill)

    return sorted(cleaned)


# -----------------------------------------------------------------------------
# Public interface
# -----------------------------------------------------------------------------

def extract_skills(
    resume_text: str,
    skills_file_path: str = "data/skills_list.txt"
) -> dict:
    """
    Main entry point. Extracts skills from resume plain text using two methods:
    1. Keyword matching against a curated skills list
    2. spaCy NER for additional tech terms not in the list

    Parameters
    ----------
    resume_text : str
        Plain text content of the resume (output of file_parser.parse_resume).
    skills_file_path : str
        Path to the curated skills list text file.
        Defaults to data/skills_list.txt.

    Returns
    -------
    dict with keys:
        - matched_skills   : list — skills found via keyword matching
        - ner_skills       : list — additional skills found via spaCy NER
        - all_skills       : list — combined deduplicated sorted list
        - total_count      : int  — total number of unique skills found

    Raises
    ------
    FileNotFoundError
        If skills_list.txt does not exist.
    ValueError
        If resume_text is empty.
    """

    # 1. Validate input
    if not resume_text or not resume_text.strip():
        raise ValueError("Resume text is empty. Please parse the file first.")

    # 2. Load the curated skills list
    skills_list = _load_skills_list(skills_file_path)

    # 3. Keyword matching
    matched_skills = _extract_by_keyword_match(resume_text, skills_list)

    # 4. NER-based extraction
    ner_skills = _extract_by_ner(resume_text)

    # 5. Remove from ner_skills anything already caught by keyword matching
    #    to keep the two lists clean and non-overlapping
    ner_only_skills = ner_skills - matched_skills

    # 6. Combine everything
    all_skills = matched_skills | ner_only_skills

    # 7. Clean and sort
    matched_clean  = _clean_skills(matched_skills)
    ner_clean      = _clean_skills(ner_only_skills)
    all_clean      = _clean_skills(all_skills)

    return {
        "matched_skills": matched_clean,
        "ner_skills":     ner_clean,
        "all_skills":     all_clean,
        "total_count":    len(all_clean),
    }


# -----------------------------------------------------------------------------
# Quick manual test
# python modules/skills_extractor.py
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    # Sample resume text for quick testing without needing a real file
    sample_text = """
    John Doe
    Software Engineer

    Skills:
    Python, Django, REST APIs, PostgreSQL, Docker, Git, AWS, React, JavaScript

    Experience:
    Developed microservices using Python and FastAPI.
    Deployed applications on AWS using Docker and Kubernetes.
    Built front-end components in React and TypeScript.

    Education:
    B.Sc. Computer Science, University of Karachi, 2020
    """

    skills_file = sys.argv[1] if len(sys.argv) > 1 else "data/skills_list.txt"

    print("\nRunning skills extraction on sample text...")
    print("-" * 60)

    try:
        result = extract_skills(sample_text, skills_file_path=skills_file)

        print(f"Matched via keyword list ({len(result['matched_skills'])}):")
        for skill in result["matched_skills"]:
            print(f"  - {skill}")

        print(f"\nFound via NER ({len(result['ner_skills'])}):")
        for skill in result["ner_skills"]:
            print(f"  - {skill}")

        print(f"\nAll skills combined ({result['total_count']}):")
        for skill in result["all_skills"]:
            print(f"  - {skill}")

    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}")
        sys.exit(1)