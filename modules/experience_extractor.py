# =============================================================================
# experience_extractor.py
# =============================================================================
# Responsibility : Extract work experience from resume plain text.
#                 Finds job titles, company names, date ranges, and
#                 calculates total years of experience.
# Used by       : main.py, jd_matcher.py
# Dependencies  : spaCy, re, datetime
# =============================================================================

import re
from datetime import datetime
import spacy


# -----------------------------------------------------------------------------
# Load spaCy model once at module level
# -----------------------------------------------------------------------------

try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    raise OSError(
        "spaCy model not found. Please run:\n"
        "python -m spacy download en_core_web_sm"
    )


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# Common section headers that signal the start of work experience
EXPERIENCE_HEADERS = [
    "experience",
    "work experience",
    "professional experience",
    "employment history",
    "work history",
    "career history",
    "positions held",
    "relevant experience",
]

# Common job title keywords to help identify title lines
JOB_TITLE_KEYWORDS = [
    "engineer", "developer", "manager", "analyst", "designer",
    "architect", "consultant", "director", "lead", "head",
    "specialist", "coordinator", "administrator", "officer",
    "executive", "intern", "associate", "senior", "junior",
    "full stack", "frontend", "backend", "devops", "data scientist",
    "product manager", "project manager", "scrum master",
    "software", "systems", "network", "security", "cloud",
    "machine learning", "ai", "research", "marketing", "sales",
]

# Month name variations for date parsing
MONTH_PATTERN = (
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|"
    r"may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|"
    r"oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
)

# Full date range pattern — matches things like:
# "Jan 2020 - Dec 2022", "March 2019 – Present", "2018 - 2021"
DATE_RANGE_PATTERN = re.compile(
    rf"({MONTH_PATTERN}\s+)?"      # optional month
    rf"(\d{{4}})"                   # start year
    rf"\s*[-–—to]+\s*"             # separator
    rf"({MONTH_PATTERN}\s+)?"      # optional end month
    rf"(\d{{4}}|present|current|now|till date|to date)",  # end year or present
    re.IGNORECASE
)


# -----------------------------------------------------------------------------
# Internal helpers
# -----------------------------------------------------------------------------

def _extract_experience_section(text: str) -> str:
    """
    Try to isolate the work experience section from the full resume text.
    Looks for common section headers and returns text from that point
    until the next major section header is found.
    If no experience section is found, returns the full text.
    """
    lines = text.splitlines()
    start_index = None

    # Next section headers that would signal end of experience section
    other_headers = [
        "education", "skills", "certifications", "projects",
        "awards", "publications", "languages", "interests",
        "references", "summary", "objective", "profile",
    ]

    for i, line in enumerate(lines):
        line_lower = line.strip().lower()

        # Find the start of the experience section
        if start_index is None:
            for header in EXPERIENCE_HEADERS:
                if line_lower == header or line_lower.startswith(header):
                    start_index = i
                    break

        # Find the end of the experience section
        elif start_index is not None and i > start_index + 1:
            for header in other_headers:
                if line_lower == header or line_lower.startswith(header):
                    return "\n".join(lines[start_index:i])

    # If we found the start but no end, return from start to end of text
    if start_index is not None:
        return "\n".join(lines[start_index:])

    # No section header found — return full text as fallback
    return text


def _parse_year(year_str: str) -> int:
    """
    Convert a year string to an integer.
    If the string is 'present', 'current', etc., return the current year.
    """
    year_str = year_str.strip().lower()

    if year_str in ("present", "current", "now", "till date", "to date"):
        return datetime.now().year

    try:
        return int(year_str)
    except ValueError:
        return datetime.now().year


def _extract_date_ranges(text: str) -> list:
    """
    Find all date ranges in the text using regex.
    Returns a list of dicts with start_year, end_year, and duration_years.
    """
    date_ranges = []
    seen = set()

    for match in DATE_RANGE_PATTERN.finditer(text):
        full_match = match.group(0).strip()

        if full_match in seen:
            continue
        seen.add(full_match)

        # Extract start and end years from capture groups
        start_year = _parse_year(match.group(2))
        end_year   = _parse_year(match.group(4))

        # Sanity check — start should be before or equal to end
        if start_year > end_year:
            start_year, end_year = end_year, start_year

        duration = end_year - start_year

        date_ranges.append({
            "raw":            full_match,
            "start_year":     start_year,
            "end_year":       end_year,
            "duration_years": duration,
        })

    return date_ranges


def _extract_job_titles(text: str) -> list:
    """
    Find likely job title lines by checking for known title keywords.
    Also uses spaCy NER to catch company names on the same line.
    Returns a list of dicts with title and company where detectable.
    """
    doc = nlp(text)

    # Get all ORG entities from spaCy to help identify company names
    org_entities = {ent.text.strip() for ent in doc.ents if ent.label_ == "ORG"}

    titles = []
    seen_titles = set()
    lines = text.splitlines()

    for line in lines:
        line_stripped = line.strip()
        line_lower = line_stripped.lower()

        if not line_stripped:
            continue

        # Check if any job title keyword appears in this line
        is_title_line = any(
            keyword in line_lower for keyword in JOB_TITLE_KEYWORDS
        )

        if is_title_line and line_stripped not in seen_titles:
            seen_titles.add(line_stripped)

            # Try to detect company name on the same line
            company = None
            for org in org_entities:
                if org.lower() in line_lower:
                    company = org
                    break

            titles.append({
                "title":   line_stripped,
                "company": company,
            })

    return titles


def _calculate_total_experience(date_ranges: list) -> float:
    """
    Calculate total years of experience from all date ranges.
    Handles overlapping periods by using the min start and max end year.
    Returns total years as a float rounded to 1 decimal place.
    """
    if not date_ranges:
        return 0.0

    # Use overall span to avoid double-counting overlapping roles
    all_start_years = [d["start_year"] for d in date_ranges]
    all_end_years   = [d["end_year"]   for d in date_ranges]

    earliest_start = min(all_start_years)
    latest_end     = max(all_end_years)

    total = latest_end - earliest_start

    return round(max(total, 0.0), 1)


# -----------------------------------------------------------------------------
# Public interface
# -----------------------------------------------------------------------------

def extract_experience(resume_text: str) -> dict:
    """
    Main entry point. Extracts work experience details from resume plain text.

    Parameters
    ----------
    resume_text : str
        Plain text content of the resume (output of file_parser.parse_resume).

    Returns
    -------
    dict with keys:
        - job_titles        : list of dicts with 'title' and 'company'
        - date_ranges       : list of dicts with 'raw', 'start_year',
                              'end_year', 'duration_years'
        - total_experience  : float — total years of experience
        - experience_level  : str   — 'Entry', 'Mid', 'Senior', or 'Executive'

    Raises
    ------
    ValueError
        If resume_text is empty.
    """

    # 1. Validate input
    if not resume_text or not resume_text.strip():
        raise ValueError("Resume text is empty. Please parse the file first.")

    # 2. Try to isolate the experience section
    experience_text = _extract_experience_section(resume_text)

    # 3. Extract date ranges and job titles
    date_ranges = _extract_date_ranges(experience_text)
    job_titles  = _extract_job_titles(experience_text)

    # 4. Calculate total experience
    total_experience = _calculate_total_experience(date_ranges)

    # 5. Classify experience level
    if total_experience < 2:
        experience_level = "Entry"
    elif total_experience < 5:
        experience_level = "Mid"
    elif total_experience < 10:
        experience_level = "Senior"
    else:
        experience_level = "Executive"

    return {
        "job_titles":       job_titles,
        "date_ranges":      date_ranges,
        "total_experience": total_experience,
        "experience_level": experience_level,
    }


# -----------------------------------------------------------------------------
# Quick manual test
# python modules/experience_extractor.py
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    sample_text = """
    John Doe
    Software Engineer

    Work Experience

    Senior Software Engineer — TechCorp
    January 2021 - Present
    Led development of microservices architecture using Python and Docker.
    Managed a team of 5 engineers.

    Software Developer — StartupXYZ
    March 2018 - December 2020
    Built REST APIs using Django and PostgreSQL.
    Worked on CI/CD pipelines using GitHub Actions.

    Junior Developer — WebAgency
    June 2016 - February 2018
    Developed frontend components using React and JavaScript.

    Education
    B.Sc. Computer Science, University of Karachi, 2016
    """

    print("\nRunning experience extraction on sample text...")
    print("-" * 60)

    try:
        result = extract_experience(sample_text)

        print(f"Experience level : {result['experience_level']}")
        print(f"Total experience : {result['total_experience']} years")

        print(f"\nJob titles found ({len(result['job_titles'])}):")
        for entry in result["job_titles"]:
            company = entry["company"] or "company not detected"
            print(f"  - {entry['title']} | {company}")

        print(f"\nDate ranges found ({len(result['date_ranges'])}):")
        for dr in result["date_ranges"]:
            print(f"  - {dr['raw']} ({dr['duration_years']} years)")

    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)