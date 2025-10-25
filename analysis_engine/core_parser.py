"""
core_parser.py

Improved resume parsing utilities with safer SpaCy loading, robust file handling,
better skill matching (including punctuation and aliases), safer date parsing,
more tolerant experience/project extraction heuristics, and optional phone parsing.

Dependencies:
- spacy
- python-docx (docx)
- pdfplumber
- (optional) phonenumbers

Install missing packages:
    pip install spacy python-docx pdfplumber phonenumbers
    python -m spacy download en_core_web_sm

Usage:
    from core_parser import parse_resume_details
    result = parse_resume_details(file_bytes, filename)
"""
from __future__ import annotations

import io
import logging
import os
import re
from typing import Dict, List, Optional, Tuple

import docx
import pdfplumber
import spacy
from spacy.matcher import Matcher

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# --- Configuration ---
MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB limit for uploaded files

# --- Lazy SpaCy loader ---
_NLP_MODEL: Optional[spacy.language.Language] = None


def get_nlp():
    global _NLP_MODEL
    if _NLP_MODEL is None:
        try:
            _NLP_MODEL = spacy.load("en_core_web_sm")
        except OSError as exc:
            logger.error(
                "SpaCy model 'en_core_web_sm' not found. Install it with: "
                "python -m spacy download en_core_web_sm"
            )
            raise RuntimeError("SpaCy model 'en_core_web_sm' not installed") from exc
    return _NLP_MODEL


# --- Skill lists and alias mapping (canonical keys in SKILLS_LIST) ---
SKILLS_LIST = [
    "python",
    "java",
    "c++",
    "c#",
    "go",
    "rust",
    "javascript",
    "typescript",
    "html",
    "css",
    "sql",
    "nosql",
    "postgresql",
    "mongodb",
    "redis",
    "git",
    "docker",
    "kubernetes",
    "aws",
    "azure",
    "gcp",
    "terraform",
    "react",
    "angular",
    "vue",
    "svelte",
    "node.js",
    "django",
    "flask",
    "fastapi",
    "spring boot",
    "machine learning",
    "deep learning",
    "data analysis",
    "pandas",
    "numpy",
    "scikit-learn",
    "tensorflow",
    "pytorch",
    "nlp",
    "computer vision",
    "agile",
    "scrum",
    "jira",
    "rest api",
    "graphql",
    "microservices",
    "cicd",
    "jenkins",
    "github actions",
    "etl",
    "data warehousing",
    "apache spark",
]

# Aliases help detect alternate spellings / punctuation variants
SKILLS_ALIASES = {
    "node.js": ["nodejs", "node"],
    "c++": ["cpp"],
    "c#": ["csharp"],
    "github actions": ["github-actions", "githubactions"],
    "rest api": ["rest", "restapi"],
    "spring boot": ["springboot"],
    "machine learning": ["ml", "machine-learning"],
    "deep learning": ["deep-learning", "dl"],
    "apache spark": ["spark"],
    "sql": ["structured query language"],
}

# Normalization mapping to preserve display-casing for special tokens
SKILL_NORMALIZE = {
    "c++": "C++",
    "c#": "C#",
    "node.js": "Node.js",
    "aws": "AWS",
    "gcp": "GCP",
    "ci/cd": "CI/CD",
    "github actions": "GitHub Actions",
    "nlp": "NLP",
    "api": "API",
    "sql": "SQL",
    "nosql": "NoSQL",
    "postgresql": "PostgreSQL",
    "mongodb": "MongoDB",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "tensorflow": "TensorFlow",
    "pytorch": "PyTorch",
    "fastapi": "FastAPI",
    "spring boot": "Spring Boot",
}


def normalize_skill(s: str) -> str:
    key = s.strip().lower()
    if key in SKILL_NORMALIZE:
        return SKILL_NORMALIZE[key]
    # Preserve common capitalization for multi-word tokens
    return " ".join(w.capitalize() if len(w) > 1 else w for w in key.split())


# --- File text extraction ---
def extract_text_from_file(file_content: bytes, filename: str) -> str:
    """
    Extract plain text from a .pdf or .docx file. Validates maximum file size.
    Raises ValueError on unsupported file or corruption.
    """
    if not file_content:
        raise ValueError("Empty file content")

    if len(file_content) > MAX_FILE_BYTES:
        raise ValueError("File too large ( > {} bytes )".format(MAX_FILE_BYTES))

    extension = os.path.splitext(filename)[1].lower()
    try:
        if extension == ".docx":
            doc = docx.Document(io.BytesIO(file_content))
            text = "\n".join(para.text for para in doc.paragraphs)
            return text
        elif extension == ".pdf":
            with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                pages = []
                for page in pdf.pages:
                    try:
                        pages.append(page.extract_text() or "")
                    except Exception:
                        # continue extracting remaining pages even if one page fails
                        logger.exception("Failed to extract text from a PDF page")
                        pages.append("")
                return "\n".join(pages)
        else:
            raise ValueError(f"Unsupported file format: {extension}")
    except Exception as exc:
        logger.exception("Failed to extract text from %s", filename)
        raise ValueError(f"Could not read file: {filename}. It may be corrupted.") from exc


# --- Contact extraction (email + phone) ---
def extract_contact_info(text: str) -> Dict[str, Optional[str]]:
    email_match = re.search(r'[\w\.\-+]+@[\w\.\-]+\.\w+', text)
    email = email_match.group(0) if email_match else None

    phone = None
    # Prefer using phonenumbers if available for robust international parsing
    try:
        import phonenumbers

        for match in re.finditer(r'[\+\d][\d\-\s().]{6,}\d', text):
            candidate = match.group(0)
            try:
                pn = phonenumbers.parse(candidate, None)
                if phonenumbers.is_possible_number(pn) and phonenumbers.is_valid_number(pn):
                    phone = phonenumbers.format_number(pn, phonenumbers.PhoneNumberFormat.E164)
                    break
            except Exception:
                continue
    except Exception:
        # Fallback to a broader regex (less strict)
        phone_match = re.search(r'(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{3,4}', text)
        phone = phone_match.group(0).strip() if phone_match else None

    return {"email": email, "phone": phone}


# --- Skill extraction ---
def extract_skills(text: str) -> List[str]:
    """
    Find skills using SKILLS_LIST + SKILLS_ALIASES.
    Uses alphanumeric-aware boundaries so punctuation like 'C++' or 'Node.js' match.
    Returns canonical normalized names (readable casing).
    """
    found = set()
    if not text:
        return []

    # Collapse multiple whitespace for more reliable matching
    clean_text = re.sub(r'\s+', ' ', text)

    for skill in SKILLS_LIST:
        candidates = [skill] + SKILLS_ALIASES.get(skill, [])
        for cand in candidates:
            # Use lookarounds that consider alphanumeric characters as boundaries (not punctuation)
            pattern = r'(?<![A-Za-z0-9_])' + re.escape(cand) + r'(?![A-Za-z0-9_])'
            if re.search(pattern, clean_text, re.IGNORECASE):
                found.add(skill.lower())
                break

    # Return normalized display names, sorted
    return [normalize_skill(s) for s in sorted(found)]


# --- Date range parsing ---
def _parse_date_range(text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse date ranges like:
      Jan 2020 - Present
      2019 - 2021
      June 2022 - Sep 2023
    Returns (start_date_str, end_date_str) or (None, None)
    """
    if not text:
        return None, None

    # Match patterns with various dash types and 'Present/Current'
    pattern = re.compile(
        r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|'
        r'January|February|March|April|May|June|July|August|September|October|November|December|'
        r'\d{4})[\s.,-]*\d{0,2}\s*\d{0,2}?)\s*[-–—]\s*(Present|Current|(?:'
        r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|'
        r'January|February|March|April|May|June|July|August|September|October|November|December|'
        r'\d{4})[\s.,-]*\d{0,2}\s*\d{0,2}?))',
        re.IGNORECASE,
    )

    match = pattern.search(text)
    if match:
        start = match.group(1)
        # group 2 is either 'Present'/'Current' or a concrete date; normalize choice
        end_candidate = match.group(2)
        if end_candidate:
            end = end_candidate
        else:
            end = None
        return (start.strip() if start else None, end.strip() if end else None)
    return None, None


# --- Name extraction ---
def extract_name(doc: spacy.tokens.Doc) -> Optional[str]:
    """
    Improved name extraction:
      1) Check the first few non-empty lines for a likely name (2-3 words, capitalized)
      2) Fall back to PERSON entity from NER
      3) Fallback to None
    """
    text = doc.text or ""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    # Check the first 6 lines for a name-like line
    for line in lines[:6]:
        # skip obvious headings
        if re.search(r'\b(resume|cv|curriculum|profile|contact)\b', line, flags=re.I):
            continue
        tokens = line.split()
        if 1 < len(tokens) <= 4:
            # check for words starting with uppercase letter
            if all(re.match(r'^[A-Z0-9\(\)\.\'#\+\-]', tok) for tok in tokens[:3]):
                # Avoid picking a company name with words like 'Inc', 'LLC'
                if not re.search(r'\b(inc|llc|ltd|solutions|technologies|technologies|corp)\b', line, flags=re.I):
                    return line.strip()

    # Fallback: PERSON entity in the entire doc
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            return ent.text.strip()

    return None


# --- Experience extraction ---
def extract_experience(text: str) -> List[Dict]:
    """
    Heuristic approach to extract experience blocks.
    - Splits by the EXPERIENCE / WORK HISTORY header if present, else uses the entire text.
    - Splits job entries using blank-line separators (robust to formatting variants).
    - Uses NER to extract ORG and DATE. Attempts to infer title/company from first lines.
    """
    nlp = get_nlp()
    experiences: List[Dict] = []

    # isolate experience section if header exists
    parts = re.split(r'\n\s*(?:EXPERIENCE|WORK HISTORY|EMPLOYMENT|PROFESSIONAL EXPERIENCE)\s*\n', text, flags=re.IGNORECASE)
    section = parts[1] if len(parts) > 1 else text

    # split on double newlines (common separator between roles)
    chunks = [c.strip() for c in re.split(r'\n\s*\n', section) if c.strip()]

    for chunk in chunks:
        if len(chunk) < 30:
            continue

        # create doc for NER
        doc = nlp(chunk)

        # Gather ORG and DATE entities
        orgs = [ent.text.strip() for ent in doc.ents if ent.label_ == "ORG"]
        dates = [ent.text.strip() for ent in doc.ents if ent.label_ == "DATE"]

        # heuristics for first line as title/company
        lines = [ln.strip() for ln in chunk.splitlines() if ln.strip()]
        title = None
        company = None

        if lines:
            first = lines[0]
            # patterns like "Senior Backend Engineer, ACME Corp" or "ACME Corp — Senior Backend Engineer"
            # try to split by separators
            sep_parts = re.split(r'[,–—\-|]', first)
            if len(sep_parts) >= 2:
                # decide which part looks like a company (contains Corp/Inc/LLP/Technologies) vs title
                for part in sep_parts:
                    if re.search(r'\b(Inc|LLC|Ltd|Technologies|Solutions|Systems|Corp|Company|Labs|Pvt|Private|LLP)\b', part, flags=re.I):
                        company = part.strip()
                    else:
                        # likely title
                        if not title:
                            title = part.strip()
                # If we found a company and a title, good.
            else:
                # If only one part, it's ambiguous; prefer using NER ORG for company or PERSON for roles
                title_candidate = first
                # If we have ORG from NER, use first ORG as company and set title to the remaining text if any
                if orgs:
                    company = orgs[0]
                    # try to remove company from the first line
                    remainder = first.replace(company, "").strip(" ,–—-|")
                    if remainder:
                        title = remainder
                else:
                    # assume first is title if it contains common seniority keywords or letters
                    if re.search(r'\b(Engineer|Developer|Manager|Director|Intern|Consultant|Analyst|Lead|SDE)\b', first, flags=re.I):
                        title = first
                    else:
                        # fallback: treat as title
                        title = first

        # If company still unknown, try NER ORG
        if not company and orgs:
            company = orgs[0]

        # Parse date range from chunk (look across entire chunk)
        start_date, end_date = _parse_date_range(chunk)

        # Extract technologies mentioned in this chunk
        technologies = extract_skills(chunk)

        # Description: we can use the chunk minus first line (to avoid repeating title)
        description = "\n".join(lines[1:]) if len(lines) > 1 else chunk

        experiences.append(
            {
                "title": (title or "Role Not Specified").strip(),
                "company": (company or "Company Not Specified").strip(),
                "start_date": start_date,
                "end_date": end_date,
                "description": description.strip(),
                "technologies": technologies,
            }
        )

    return experiences


# --- Project extraction ---
def extract_projects(text: str) -> List[Dict]:
    """
    Extracts projects from PROJECTS / PERSONAL PROJECTS section.
    Falls back to looking for lines containing 'Project' keywords if header absent.
    """
    nlp = get_nlp()
    projects: List[Dict] = []

    parts = re.split(r'\n\s*(?:PROJECTS?|PERSONAL PROJECTS|PROJECT HIGHLIGHTS)\s*\n', text, flags=re.IGNORECASE)
    project_text = parts[1] if len(parts) > 1 else ""

    if not project_text:
        # quick heuristic: find sections with 'project' word near it
        matches = re.findall(r'((?:[A-Z][^\n]{10,200}\n(?:.+\n){0,6}))', text)
        # We'll be conservative: only continue if the matches look project-like
        project_chunks = []
        for m in matches:
            if "project" in m.lower() or "github.com" in m.lower():
                project_chunks.append(m.strip())
    else:
        # Split projects by double newlines
        project_chunks = [c.strip() for c in re.split(r'\n\s*\n', project_text) if c.strip()]

    for chunk in project_chunks:
        if len(chunk) < 20:
            continue
        lines = [ln.strip() for ln in chunk.splitlines() if ln.strip()]
        title = lines[0] if lines else "Untitled Project"
        description = " ".join(lines[1:]) if len(lines) > 1 else ""
        # Try to find a stack/technology line
        tech_line_match = re.search(r'(?:Technologies|Stack|Tools Used|Tech Stack)[:\s]+(.+)', chunk, re.IGNORECASE)
        if tech_line_match:
            technologies = [normalize_skill(t) for t in re.split(r'[,\|;]', tech_line_match.group(1)) if t.strip()]
            # remove tech line from description
            description = re.sub(re.escape(tech_line_match.group(0)), "", description, flags=re.IGNORECASE).strip()
        else:
            technologies = extract_skills(chunk)

        # Link detection (github, http/https)
        link_match = re.search(r'(https?://[^\s\)\]]+)', chunk)
        link = link_match.group(1) if link_match else None

        projects.append(
            {
                "title": title.strip(),
                "description": description.strip(),
                "technologies": technologies,
                "link": link,
            }
        )

    return projects


# --- Education extraction (basic) ---
def extract_education(text: str) -> List[Dict]:
    """
    Extracts education blocks from EDUCATION / ACADEMIC section.
    Tries to capture degree, institution, year, and grade if present.
    """
    edus: List[Dict] = []
    parts = re.split(r'\n\s*(?:EDUCATION|ACADEMIC|QUALIFICATIONS|EDUCATION & CREDENTIALS)\s*\n', text, flags=re.IGNORECASE)
    edu_text = parts[1] if len(parts) > 1 else ""

    if not edu_text:
        return edus

    chunks = [c.strip() for c in re.split(r'\n\s*\n', edu_text) if c.strip()]
    for chunk in chunks:
        # Look for degree names and year/percentage
        degree_match = re.search(r'(Bachelor|B\.Tech|BTech|B\.E|B\.S|Master|M\.Tech|MTech|M\.S|Bachelors|Masters|PhD|Graduat)', chunk, re.IGNORECASE)
        year_match = re.search(r'\b(19|20)\d{2}\b', chunk)
        grade_match = re.search(r'(\bGPA[:\s]*[0-9]\.?[0-9]?\b|\b\d{1,2}\.\d{1,2}/10\b|\b\d{1,3}%\b)', chunk, re.IGNORECASE)
        # Institution detection using NER
        nlp = get_nlp()
        doc = nlp(chunk)
        orgs = [ent.text for ent in doc.ents if ent.label_ == "ORG"]
        institution = orgs[0] if orgs else None

        edus.append(
            {
                "degree": degree_match.group(0) if degree_match else None,
                "institution": institution,
                "year": year_match.group(0) if year_match else None,
                "grade": grade_match.group(0) if grade_match else None,
                "description": chunk,
            }
        )

    return edus


# --- Main orchestrator ---
def parse_resume_details(file_content: bytes, filename: str) -> Dict:
    """
    Main entrypoint. Returns a dictionary with keys:
      name, contact, skills, education, projects, experience, full_text, filename
    Ensures keys are present and uses the improved parsers above.
    """
    nlp = get_nlp()  # may raise RuntimeError if model missing
    text = extract_text_from_file(file_content, filename)
    doc = nlp(text)

    name = extract_name(doc) or "Name Not Found"
    contact = extract_contact_info(text) or {"email": None, "phone": None}
    skills = extract_skills(text) or []
    experience = extract_experience(text) or []
    projects = extract_projects(text) or []
    education = extract_education(text) or []

    return {
        "name": name,
        "contact": contact,
        "skills": skills,
        "education": education,
        "projects": projects,
        "experience": experience,
        "full_text": text,
        "filename": filename,
    }

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) < 2:
        print("Usage: python core_parser.py <resume-file>")
        sys.exit(1)

    path = sys.argv[1]
    with open(path, "rb") as f:
        b = f.read()
    result = parse_resume_details(b, os.path.basename(path))
    import json

    print(json.dumps(result, indent=2, ensure_ascii=False))
