# =============================================================================
# education_extractor.py
# =============================================================================
# Responsibility : Extract education details from resume plain text.
#                 Finds degrees, institutions, fields of study,
#                 and graduation years.
# Used by       : main.py, jd_matcher.py
# Dependencies  : spaCy, re
# =============================================================================

import re
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

# Common section headers that signal the start of the education section
EDUCATION_HEADERS = [
    "education",
    "academic background",
    "academic qualifications",
    "qualifications",
    "academic history",
    "educational background",
    "degrees",
]

# Degree types mapped to a clean standard label
DEGREE_PATTERNS = {
    # Doctoral
    "phd":        "PhD",
    "ph.d":       "PhD",
    "doctorate":  "PhD",
    "doctoral":   "PhD",

    # Masters
    "master":     "Masters",
    "masters":    "Masters",
    "m.sc":       "Masters",
    "msc":        "Masters",
    "m.s":        "Masters",
    "ms":         "Masters",
    "m.eng":      "Masters",
    "meng":       "Masters",
    "mba":        "MBA",
    "m.b.a":      "MBA",
    "m.a":        "Masters",
    "ma":         "Masters",

    # Bachelors
    "bachelor":   "Bachelors",
    "bachelors":  "Bachelors",
    "b.sc":       "Bachelors",
    "bsc":        "Bachelors",
    "b.s":        "Bachelors",
    "bs":         "Bachelors",
    "b.eng":      "Bachelors",
    "beng":       "Bachelors",
    "b.tech":     "Bachelors",
    "btech":      "Bachelors",
    "b.a":        "Bachelors",
    "ba":         "Bachelors",
    "b.com":      "Bachelors",
    "bcom":       "Bachelors",

    # Associates
    "associate":  "Associates",
    "associates": "Associates",
    "a.s":        "Associates",
    "a.a":        "Associates",

    # Diploma & Certificate
    "diploma":    "Diploma",
    "certificate":"Certificate",
    "certification":"Certificate",
    "hnd":        "HND",
    "hnc":        "HNC",

    # High School
    "high school":      "High School",
    "secondary school": "High School",
    "gcse":             "High School",
    "a-level":          "High School",
    "a level":          "High School",
    "matric":           "High School",
    "matriculation":    "High School",
    "intermediate":     "Intermediate",
    "o-level":          "High School",
    "o level":          "High School",
}

# Common fields of study keywords
FIELD_KEYWORDS = [
    "computer science", "software engineering", "information technology",
    "data science", "artificial intelligence", "machine learning",
    "electrical engineering", "mechanical engineering", "civil engineering",
    "business administration", "finance", "economics", "accounting",
    "mathematics", "statistics", "physics", "chemistry", "biology",
    "psychology", "sociology", "communications", "marketing",
    "graphic design", "architecture", "law", "medicine", "nursing",
    "information systems", "cybersecurity", "network engineering",
    "human resources", "management", "supply chain", "logistics",
]

# Graduation year pattern — 4 digit year between 1950 and current year + 6
YEAR_PATTERN = re.compile(r"\b(19[5-9]\d|20[0-3]\d)\b")


# -----------------------------------------------------------------------------
# Internal helpers
# -----------------------------------------------------------------------------

def _extract_education_section(text: str) -> str:
    """
    Try to isolate the education section from the full resume text.
    Returns text from the education header to the next major section.
    Falls back to full text if no header is found.
    """
    lines = text.splitlines()
    start_index = None

    other_headers = [
        "experience", "work experience", "professional experience",
        "skills", "certifications", "projects", "awards",
        "publications", "languages", "interests", "references",
        "summary", "objective", "profile", "employment",
    ]

    for i, line in enumerate(lines):
        line_lower = line.strip().lower()

        if start_index is None:
            for header in EDUCATION_HEADERS:
                if line_lower == header or line_lower.startswith(header):
                    start_index = i
                    break

        elif i > start_index + 1:
            for header in other_headers:
                if line_lower == header or line_lower.startswith(header):
                    return "\n".join(lines[start_index:i])

    if start_index is not None:
        return "\n".join(lines[start_index:])

    return text


def _detect_degree(line: str) -> str | None:
    """
    Check a line of text for any known degree pattern.
    Returns the standardised degree label or None if not found.
    """
    line_lower = line.lower()

    for pattern, label in DEGREE_PATTERNS.items():
        # Use word boundary matching for short abbreviations
        escaped = re.escape(pattern)
        if re.search(rf"\b{escaped}\b", line_lower):
            return label

    return None


def _detect_field(line: str) -> str | None:
    """
    Check a line for a known field of study keyword.
    Returns the matched field or None.
    """
    line_lower = line.lower()

    for field in FIELD_KEYWORDS:
        if field in line_lower:
            return field.title()

    return None


def _detect_institution(line: str, org_entities: set) -> str | None:
    """
    Try to detect a university or institution name on a line.
    Uses two methods:
    1. spaCy ORG entities detected in the full text
    2. Keyword heuristic — lines containing 'university', 'college' etc.
    """
    line_lower = line.lower()

    # Method 1 — spaCy ORG match
    for org in org_entities:
        if org.lower() in line_lower:
            return org

    # Method 2 — heuristic keyword match
    institution_keywords = [
        "university", "college", "institute", "school",
        "academy", "polytechnic", "faculty", "campus",
    ]
    for keyword in institution_keywords:
        if keyword in line_lower:
            # Return the full line as the institution name (cleaned up)
            return line.strip()

    return None


def _detect_year(line: str) -> int | None:
    """
    Find a 4-digit graduation year in a line.
    Returns the last year found (most likely the graduation year)
    or None if no year is present.
    """
    years = YEAR_PATTERN.findall(line)
    if years:
        return int(years[-1])  # take the last year on the line
    return None


# -----------------------------------------------------------------------------
# Public interface
# -----------------------------------------------------------------------------

def extract_education(resume_text: str) -> dict:
    """
    Main entry point. Extracts education details from resume plain text.

    Parameters
    ----------
    resume_text : str
        Plain text content of the resume (output of file_parser.parse_resume).

    Returns
    -------
    dict with keys:
        - education_entries : list of dicts, each with:
                              'degree', 'field', 'institution', 'year'
        - highest_degree    : str  — the most advanced degree found
        - total_entries     : int  — number of education entries found

    Raises
    ------
    ValueError
        If resume_text is empty.
    """

    # 1. Validate input
    if not resume_text or not resume_text.strip():
        raise ValueError("Resume text is empty. Please parse the file first.")

    # 2. Isolate the education section
    education_text = _extract_education_section(resume_text)

    # 3. Run spaCy on the section to get ORG entities
    doc = nlp(education_text)
    org_entities = {
        ent.text.strip()
        for ent in doc.ents
        if ent.label_ == "ORG"
    }

    # 4. Go line by line and build education entries
    lines = education_text.splitlines()
    entries = []
    current_entry = {}

    for line in lines:
        stripped = line.strip()
        if not stripped:
            # Blank line — save current entry if it has content
            if current_entry:
                entries.append(current_entry)
                current_entry = {}
            continue

        degree      = _detect_degree(stripped)
        field       = _detect_field(stripped)
        institution = _detect_institution(stripped, org_entities)
        year        = _detect_year(stripped)

        # Merge findings into the current entry
        if degree and "degree" not in current_entry:
            current_entry["degree"] = degree
        if field and "field" not in current_entry:
            current_entry["field"] = field
        if institution and "institution" not in current_entry:
            current_entry["institution"] = institution
        if year and "year" not in current_entry:
            current_entry["year"] = year

        # If this line has a degree, it's likely a new entry starting
        if degree and len(current_entry) > 1:
            # Save whatever was built so far as a complete entry
            # and start fresh with just this degree line
            if "degree" in current_entry:
                entries.append(current_entry)
                current_entry = {"degree": degree}
                if field:
                    current_entry["field"] = field
                if year:
                    current_entry["year"] = year

    # Save the last entry if it has content
    if current_entry:
        entries.append(current_entry)

    # 5. Clean entries — remove ones with no useful info
    clean_entries = []
    for entry in entries:
        if any(k in entry for k in ("degree", "institution", "field")):
            # Fill in any missing fields with None for consistency
            clean_entries.append({
                "degree":      entry.get("degree",      None),
                "field":       entry.get("field",       None),
                "institution": entry.get("institution", None),
                "year":        entry.get("year",        None),
            })

    # 6. Determine highest degree
    degree_rank = {
        "PhD":         6,
        "MBA":         5,
        "Masters":     4,
        "Bachelors":   3,
        "Associates":  2,
        "Diploma":     1,
        "Certificate": 1,
        "HND":         1,
        "HNC":         1,
        "Intermediate":0,
        "High School": 0,
    }

    highest_degree = None
    highest_rank   = -1

    for entry in clean_entries:
        deg = entry.get("degree")
        if deg and degree_rank.get(deg, -1) > highest_rank:
            highest_rank   = degree_rank[deg]
            highest_degree = deg

    return {
        "education_entries": clean_entries,
        "highest_degree":    highest_degree,
        "total_entries":     len(clean_entries),
    }


# -----------------------------------------------------------------------------
# Quick manual test
# python modules/education_extractor.py
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    sample_text = """
    John Doe
    Software Engineer

    Education

    M.Sc. Computer Science
    University of Karachi, 2022
    Specialisation in Machine Learning and Data Science

    B.Sc. Software Engineering
    FAST National University, 2020
    Graduated with distinction

    Intermediate (Pre-Engineering)
    Army Public School, 2016

    Work Experience

    Senior Software Engineer — TechCorp
    January 2021 - Present
    """

    print("\nRunning education extraction on sample text...")
    print("-" * 60)

    try:
        result = extract_education(sample_text)

        print(f"Total entries found : {result['total_entries']}")
        print(f"Highest degree      : {result['highest_degree']}")

        print(f"\nEducation entries:")
        for i, entry in enumerate(result["education_entries"], 1):
            print(f"\n  Entry {i}:")
            print(f"    Degree      : {entry['degree']      or 'not detected'}")
            print(f"    Field       : {entry['field']       or 'not detected'}")
            print(f"    Institution : {entry['institution'] or 'not detected'}")
            print(f"    Year        : {entry['year']        or 'not detected'}")

    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)