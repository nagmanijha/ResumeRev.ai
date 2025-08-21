import spacy
from spacy.matcher import Matcher
import docx
import pdfplumber
import re
import os
import io
import logging
logger = logging.getLogger(__name__)

try:
    NLP_MODEL = spacy.load("en_core_web_sm")
except OSError:
    logging.error("SpaCy model 'en_core_web_sm' not found. Please run 'python -m spacy download en_core_web_sm'")
    NLP_MODEL = None

SKILLS_LIST = [ 
    'python', 'java', 'c++', 'c#', 'go', 'rust', 'javascript', 'typescript', 'html', 'css', 
    'sql', 'nosql', 'postgresql', 'mongodb', 'redis', 'git', 'docker', 'kubernetes', 'aws', 
    'azure', 'gcp', 'terraform', 'react', 'angular', 'vue', 'svelte', 'node.js', 'django',
    'flask', 'fastapi', 'spring boot', 'machine learning', 'deep learning', 'data analysis',
    'pandas', 'numpy', 'scikit-learn', 'tensorflow', 'pytorch', 'nlp', 'computer vision',
    'agile', 'scrum', 'jira', 'rest api', 'graphql', 'microservices', 'cicd', 'jenkins',
    'github actions', 'etl', 'data warehousing', 'apache spark'
]

def extract_text_from_file(file_content: bytes, filename: str) -> str:
    try:
        extension = os.path.splitext(filename)[1].lower()
        text = ""
        if extension == ".docx":
            doc = docx.Document(io.BytesIO(file_content))
            text = "\n".join([para.text for para in doc.paragraphs])
        elif extension == ".pdf":
            with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                text = "\n".join([page.extract_text() or "" for page in pdf.pages])
        else:
            raise ValueError(f"Unsupported file format: {extension}")
        return text
    except Exception as e:
        logger.error(f"Failed to extract text from {filename}: {e}", exc_info=True)
        raise ValueError(f"Could not read file: {filename}. It may be corrupted.")



def extract_name(doc: spacy.tokens.Doc) -> str | None:
    """
    Extracts the candidate's name using a multi-strategy approach.
    1. Looks for a two-word Proper Noun pattern at the start of the resume.
    2. Falls back to finding the first 'PERSON' entity.
    """
    # Strategy 1: Use Matcher for "PROPN PROPN" pattern
    matcher = Matcher(NLP_MODEL.vocab)
    pattern = [{'POS': 'PROPN'}, {'POS': 'PROPN'}]
    matcher.add('FULL_NAME', [pattern])
    
    # Search in the first 15 tokens of the document
    matches = matcher(doc[:15])
    if matches:
        # Get the span for the longest match
        match_id, start, end = max(matches, key=lambda m: m[2] - m[1])
        return doc[start:end].text.strip()

    # Strategy 2: Fallback to finding the first PERSON entity
    for ent in doc[:30].ents:
        if ent.label_ == "PERSON":
            return ent.text.strip()
            
    return "Name Not Found"

def extract_contact_info(text: str) -> dict:
    email = re.search(r'[\w\.\-+]+@[\w\.\-]+\.\w+', text)
    phone = re.search(r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text)
    return {"email": email.group(0) if email else None, "phone": phone.group(0) if phone else None}

def extract_skills(text: str) -> list[str]:
    found_skills = set()
    for skill in SKILLS_LIST:
        if re.search(r'\b' + re.escape(skill) + r'\b', text, re.IGNORECASE):
            found_skills.add(skill.lower())
    return list(found_skills)

def _parse_date_range(text: str) -> tuple[str | None, str | None]:
    """Helper function to find and parse date ranges."""
    # Regex to find dates like "Jan 2020 - Present", "2019-2021", "June 2022"
    pattern = re.compile(
        r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|June|July|August|September|October|November|December)[\s.]*\d{4})\s*-\s*(Present|Current|((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|June|July|August|September|October|November|December)[\s.]*\d{4}))',
        re.IGNORECASE
    )
    match = pattern.search(text)
    if match:
        start_date, end_date_group, end_date = match.groups()
        return start_date.strip(), end_date.strip()
    return None, None

def extract_experience(text: str) -> list[dict]:
    """
    Extracts work experience using a combination of section splitting and NLP.
    """
    experiences = []
    # Isolate the experience section first for more accurate parsing
    experience_text_block = re.split(r'\n\s*(?:EXPERIENCE|WORK HISTORY|EMPLOYMENT)\s*\n', text, flags=re.IGNORECASE)
    text_to_search = experience_text_block[1] if len(experience_text_block) > 1 else text
    
    # Split the section into chunks that likely represent individual jobs
    # A job chunk often starts with a company name or job title
    job_chunks = re.split(r'\n(?=[A-Z][a-z]+,?\s+[A-Z][a-z]+)', text_to_search) # Heuristic split

    for chunk in job_chunks:
        if len(chunk.strip()) < 50: continue # Skip very small chunks
            
        doc = NLP_MODEL(chunk)
        
        # Use NLP to find entities
        companies = [ent.text.strip() for ent in doc.ents if ent.label_ == 'ORG']
        dates = [ent.text.strip() for ent in doc.ents if ent.label_ == 'DATE']
        
        # Use regex to find job titles (often noun phrases near the top)
        title_match = re.search(r'^([A-Za-z\s,]+)\n', chunk)
        
        if title_match and companies:
            title = title_match.group(1).strip()
            # Clean up title from company name if they are the same
            if title.lower() == companies[0].lower():
                title = "Role Not Specified"

            start_date, end_date = _parse_date_range(chunk)
            
            # Extract technologies mentioned in this job description
            technologies = extract_skills(chunk)

            experiences.append({
                "title": title.title(),
                "company": companies[0],
                "start_date": start_date,
                "end_date": end_date,
                "description": chunk.strip(),
                "technologies": [t.capitalize() for t in technologies]
            })

    return experiences

def extract_projects(text: str) -> list[dict]:
    """
    Extracts project sections with more detail, looking for technologies and links.
    """
    projects = []
    project_text_block = re.split(r'\n\s*(?:PROJECTS?|PERSONAL PROJECTS)\s*\n', text, flags=re.IGNORECASE)
    text_to_search = project_text_block[1] if len(project_text_block) > 1 else ""

    if not text_to_search: return []

    # Projects are often separated by double newlines
    project_chunks = re.split(r'\n\s*\n', text_to_search)

    for chunk in project_chunks:
        chunk = chunk.strip()
        if len(chunk) < 30: continue
            
        lines = chunk.split('\n')
        title = lines[0].strip()
        description = " ".join(lines[1:])
        
        # Look for a specific "Technologies:" or "Stack:" line for higher accuracy
        tech_line_match = re.search(r'(?:Technologies|Stack|Tools Used)[:\s]+(.+)', chunk, re.IGNORECASE)
        if tech_line_match:
            technologies = [tech.strip() for tech in tech_line_match.group(1).split(',')]
            # Clean the tech line out of the main description
            description = description.replace(tech_line_match.group(0), '')
        else:
            # Fallback to searching the whole description
            technologies = extract_skills(description)
        
        # Look for a project link
        link_match = re.search(r'https?://[^\s]+', chunk)
        link = link_match.group(0) if link_match else None

        projects.append({
            "title": title.title(),
            "description": description.strip(),
            "technologies": [t.capitalize() for t in technologies],
            "link": link
        })
        
    return projects

def parse_resume_details(file_content: bytes, filename: str) -> dict:
    """
    The main parsing orchestrator function.
    FIX: This function now GUARANTEES that all keys are present in the returned dictionary.
    """
    if not NLP_MODEL:
        raise RuntimeError("SpaCy model is not loaded. Cannot parse resume.")
        
    text = extract_text_from_file(file_content, filename)
    doc = NLP_MODEL(text)
    
    # Run all extraction functions
    name = extract_name(doc)
    contact = extract_contact_info(text)
    skills = extract_skills(text)
    experience = extract_experience(text)
    projects = extract_projects(text)

   
    return {
        "name": name or "Name Not Found",
        "contact": contact or {"email": None, "phone": None},
        "skills": [s.capitalize() for s in skills] or [],
        "education": [], 
        "projects": projects or [],
        "experience": experience or [],
        "full_text": text,
        "filename": filename
    }