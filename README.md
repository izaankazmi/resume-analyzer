# 📄 AI Resume Analyzer

An AI-powered resume analysis tool that compares a candidate's resume against a job description and delivers a detailed feedback report with a match score, skill gap analysis, and personalised recommendations — sent directly to the candidate by email.

Built with Python 3.10 and Streamlit as a fully functional portfolio project.

---

## Features

- **Resume parsing** — accepts PDF and DOCX files and extracts clean plain text
- **NLP extraction** — identifies skills, work experience, job titles, education, and graduation years using spaCy
- **JD matching** — compares the resume against a job description using three scoring methods combined into one composite score
- **Skill gap analysis** — shows matched skills, missing skills, and extra skills side by side
- **Personalised recommendations** — generates actionable feedback based on score and experience level
- **HTML report generation** — renders a clean, styled feedback report using Jinja2
- **Email delivery** — sends the report directly to the candidate via Gmail SMTP or SendGrid
- **Guided wizard UI** — clean four-step Streamlit interface that walks the user through the process

---

## How the scoring works

The composite match score out of 100 is calculated using three methods:

| Method | Weight | What it measures |
|---|---|---|
| TF-IDF keyword matching | 35% | Exact keyword overlap between resume and JD |
| Semantic similarity | 45% | Meaning-level similarity using sentence transformers |
| Skills overlap | 20% | Percentage of JD-required skills found in resume |

Scores are classified as Excellent (75+), Good (55+), Fair (35+), or Low (below 35).

---

## Demo

### Step 1 — Candidate details
Enter the candidate's name, email address, and the role they are applying for.

### Step 2 — Upload resume
Upload a PDF or DOCX resume file.

### Step 3 — Job description
Paste the full job description including requirements and responsibilities.

### Step 4 — Results
View the composite score, skill tags, experience summary, education summary, and recommendations. Download the HTML report or send it to the candidate by email.

---

## Tech stack

| Category | Library | Version |
|---|---|---|
| Framework | Streamlit | 1.35.0 |
| NLP | spaCy | 3.7.5 |
| Semantic similarity | sentence-transformers | 3.0.1 |
| Keyword matching | scikit-learn | 1.5.1 |
| PDF parsing | PyMuPDF | 1.24.5 |
| DOCX parsing | python-docx | 1.1.2 |
| Report templating | Jinja2 | 3.1.4 |
| Email delivery | smtplib / SendGrid | stdlib / 6.11.0 |
| Environment config | python-dotenv | 1.0.1 |
| Language | Python | 3.10.11 |

---

## Project structure

```
resume-analyzer/
├── modules/
│   ├── file_parser.py           # PDF and DOCX text extraction
│   ├── skills_extractor.py      # spaCy NER + keyword matching
│   ├── experience_extractor.py  # Job titles and date range parsing
│   ├── education_extractor.py   # Degree and institution detection
│   ├── jd_matcher.py            # TF-IDF + semantic + skills scoring
│   ├── report_generator.py      # Jinja2 HTML report rendering
│   └── email_agent.py           # Gmail SMTP and SendGrid delivery
├── templates/
│   └── report_template.html     # HTML report template
├── data/
│   └── skills_list.txt          # Curated skills list (11 job families)
├── main.py                      # Streamlit app entry point
├── requirements.txt             # Pinned dependencies
└── .env                         # Credentials (not included in repo)
```

---

## Installation

### Prerequisites
- Python 3.10.11
- Git

### 1. Clone the repository
```bash
git clone https://github.com/izaankazmi/resume-analyzer.git
cd resume-analyzer
```

### 2. Create and activate a virtual environment
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Download the spaCy language model
```bash
python -m spacy download en_core_web_sm
```

### 5. Set up environment variables
Create a `.env` file in the project root:
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_gmail@gmail.com
SMTP_PASSWORD=your_16_character_app_password
SENDER_EMAIL=your_gmail@gmail.com
```

For Gmail, generate an App Password at:
`Google Account → Security → 2-Step Verification → App Passwords`

### 6. Run the app
```bash
streamlit run main.py
```

The app will open automatically at `http://localhost:8501`

---

## How to use

1. Open the app in your browser
2. **Step 1** — Enter the candidate's full name, email address, and the role they are applying for
3. **Step 2** — Upload their resume as a PDF or DOCX file
4. **Step 3** — Paste the full job description
5. **Step 4** — View the match score, skill analysis, and recommendations
6. Download the HTML report or click **Send Report by Email** to deliver it to the candidate

---

## Skills coverage

The skills list covers 11 job families making the analyzer suitable for a wide range of roles:

- Information Technology
- Accountancy & Finance
- Media & Communications
- Government & Public Sector
- Marketing & Advertising
- Healthcare & Medicine
- Legal & Compliance
- Engineering (non-software)
- Education & Teaching
- Human Resources & Recruitment
- Sales & Business Development

---

## Author

**Izaan Kazmi**
[github.com/izaankazmi](https://github.com/izaankazmi)

---

## License

This project is open source and available for personal and educational use.