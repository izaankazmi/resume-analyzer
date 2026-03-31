# =============================================================================
# file_parser.py
# =============================================================================
# Responsibility : Accept a PDF or DOCX file and return clean plain text.
# Used by       : main.py, and indirectly by all extractor modules.
# Dependencies  : PyMuPDF (fitz), python-docx
# =============================================================================

import os
import fitz  # PyMuPDF
from docx import Document


# -----------------------------------------------------------------------------
# Internal helpers
# -----------------------------------------------------------------------------

def _parse_pdf(file_path: str) -> str:
    """
    Extract text from a PDF file page by page.
    Returns a single string with all pages joined by newlines.
    """
    text_pages = []

    try:
        pdf = fitz.open(file_path)
    except Exception as e:
        raise ValueError(f"Could not open PDF file: {file_path}\nReason: {e}")

    for page_number in range(len(pdf)):
        page = pdf[page_number]
        page_text = page.get_text("text")  # plain text mode
        if page_text.strip():              # skip blank pages
            text_pages.append(page_text)

    pdf.close()

    if not text_pages:
        raise ValueError(f"No readable text found in PDF: {file_path}")

    return "\n".join(text_pages)


def _parse_docx(file_path: str) -> str:
    """
    Extract text from a DOCX file paragraph by paragraph.
    Returns a single string with all paragraphs joined by newlines.
    """
    try:
        doc = Document(file_path)
    except Exception as e:
        raise ValueError(f"Could not open DOCX file: {file_path}\nReason: {e}")

    paragraphs = []

    for para in doc.paragraphs:
        text = para.text.strip()
        if text:                           # skip empty paragraphs
            paragraphs.append(text)

    if not paragraphs:
        raise ValueError(f"No readable text found in DOCX: {file_path}")

    return "\n".join(paragraphs)


# -----------------------------------------------------------------------------
# Public interface — this is what the rest of the app calls
# -----------------------------------------------------------------------------

def parse_resume(file_path: str) -> str:
    """
    Main entry point. Accepts a file path to a PDF or DOCX resume.
    Returns the extracted text as a clean string.

    Parameters
    ----------
    file_path : str
        Absolute or relative path to the resume file.

    Returns
    -------
    str
        Plain text content of the resume.

    Raises
    ------
    FileNotFoundError
        If the file does not exist at the given path.
    ValueError
        If the file format is not supported, or the file has no readable text.
    """

    # 1. Check the file actually exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    # 2. Read the file extension (lowercase for safety)
    _, extension = os.path.splitext(file_path)
    extension = extension.lower()

    # 3. Route to the correct parser
    if extension == ".pdf":
        raw_text = _parse_pdf(file_path)

    elif extension == ".docx":
        raw_text = _parse_docx(file_path)

    else:
        raise ValueError(
            f"Unsupported file format: '{extension}'. "
            f"Only .pdf and .docx are accepted."
        )

    # 4. Clean up the extracted text
    cleaned_text = _clean_text(raw_text)

    return cleaned_text


def _clean_text(text: str) -> str:
    """
    Basic cleanup of raw extracted text:
    - Strip leading/trailing whitespace from each line
    - Remove lines that are completely empty after stripping
    - Collapse multiple consecutive blank lines into one
    - Return a single clean string
    """
    lines = text.splitlines()
    cleaned_lines = []

    prev_blank = False

    for line in lines:
        stripped = line.strip()

        if stripped == "":
            if not prev_blank:             # allow max one consecutive blank line
                cleaned_lines.append("")
            prev_blank = True
        else:
            cleaned_lines.append(stripped)
            prev_blank = False

    return "\n".join(cleaned_lines).strip()


# -----------------------------------------------------------------------------
# Quick manual test — run this file directly to verify it works
# python modules/file_parser.py
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python file_parser.py <path_to_resume.pdf or .docx>")
        sys.exit(1)

    path = sys.argv[1]

    print(f"\nParsing: {path}")
    print("-" * 60)

    try:
        result = parse_resume(path)
        print(result)
        print("-" * 60)
        print(f"Total characters extracted: {len(result)}")
        print(f"Total lines extracted     : {result.count(chr(10))}")

    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}")
        sys.exit(1)