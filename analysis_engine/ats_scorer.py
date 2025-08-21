import logging
import re
from datetime import datetime
import numpy as np
from textblob import TextBlob
from sentence_transformers import SentenceTransformer, util
from sklearn.feature_extraction.text import TfidfVectorizer
from rapidfuzz import process, fuzz

from .core_parser import extract_skills
from config import (
    ATS_SCORE_WEIGHTS, SEMANTIC_SKILL_MATCH_THRESHOLD, FUZZY_SKILL_MATCH_THRESHOLD,
    MODEL_NAME, ACTION_VERBS, SECTION_KEYWORDS, MAX_SKILLS_TO_MATCH
)

logger = logging.getLogger(__name__)

class ModelManager:
    _instance, _model, _is_healthy = None, None, False
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelManager, cls).__new__(cls)
            cls._instance._initialize_model()
        return cls._instance
    def _initialize_model(self):
        try:
            self._model = SentenceTransformer(MODEL_NAME)
            self._model.encode(["test"])
            self._is_healthy = True
            logger.info(f"Successfully loaded SentenceTransformer model: {MODEL_NAME}")
        except Exception as e:
            logger.error(f"FATAL: Failed to load SentenceTransformer model: {e}", exc_info=True)
    @property
    def model(self): return self._model
    @property
    def is_healthy(self): return self._is_healthy

MODEL_MANAGER = ModelManager()
BULLET_POINT_PATTERN = re.compile(r'\n\s*[\*•\-]\s*')
METRICS_PATTERN = re.compile(r'\b(\d+%?|\$\d+(?:,\d+)*(?:\.\d+)?\%?|\d+(?:\.\d+)?x)\b', re.IGNORECASE)

def _calculate_experience_duration(experience: dict) -> float:
    start_str, end_str = experience.get('start_date', ''), experience.get('end_date', 'Present')
    try:
        start_date = datetime.strptime(start_str, '%Y-%m-%d')
        end_date = datetime.now() if end_str == 'Present' else datetime.strptime(end_str, '%Y-%m-%d')
        return max(1, (end_date - start_date).days / 30.44)
    except (ValueError, TypeError): # FIX: Catch specific errors
        return 6.0

def rate_skill_levels(resume_data: dict) -> dict:
    # Your advanced skill rating logic
    skills = resume_data.get('skills', [])
    skill_experience = {skill.lower(): sum(1 for p in resume_data.get('projects', []) if skill in p.get('technologies', [])) for skill in skills}
    
    for exp in resume_data.get('experience', []):
        duration_years = _calculate_experience_duration(exp) / 12
        for tech in exp.get('technologies', []):
            if tech.lower() in skill_experience:
                skill_experience[tech.lower()] += duration_years

    skill_levels = {}
    for skill in skills:
        exp_score = skill_experience.get(skill.lower(), 0)
        if exp_score >= 3: level = 'Expert'
        elif exp_score >= 1.5: level = 'Advanced'
        elif exp_score > 0: level = 'Intermediate'
        else: level = 'Beginner'
        skill_levels[skill] = level
    return skill_levels

def match_skills_semantically(resume_skills: list[str], job_skills: list[str]) -> dict:
    if not job_skills: return {"matched": resume_skills, "missing": [], "match_percent": 100}
    if not resume_skills: return {"matched": [], "missing": job_skills, "match_percent": 0}

    resume_lower = [s.lower().strip() for s in resume_skills]
    job_lower = [s.lower().strip() for s in job_skills]
    exact_matches = set(s for s in job_lower if s in resume_lower)
    
    rem_job = [s for s in job_lower if s not in exact_matches]
    rem_resume = [s for s in resume_lower if s not in exact_matches]
    
    fuzzy_matches = set()
    if rem_job and rem_resume:
        for js in rem_job:
            match = process.extractOne(js, rem_resume, scorer=fuzz.token_set_ratio, score_cutoff=FUZZY_SKILL_MATCH_THRESHOLD)
            if match:
                fuzzy_matches.add(js)
                rem_resume.remove(match[0])

    semantic_matches = set()
    final_rem_job = [s for s in rem_job if s not in fuzzy_matches][:MAX_SKILLS_TO_MATCH]
    if MODEL_MANAGER.is_healthy and final_rem_job and rem_resume:
        job_emb = MODEL_MANAGER.model.encode(final_rem_job)
        res_emb = MODEL_MANAGER.model.encode(rem_resume[:MAX_SKILLS_TO_MATCH])
        scores = util.cos_sim(job_emb, res_emb)
        for i in range(len(final_rem_job)):
            if scores[i].max() > SEMANTIC_SKILL_MATCH_THRESHOLD:
                semantic_matches.add(final_rem_job[i])

    all_matches_lower = exact_matches.union(fuzzy_matches).union(semantic_matches)
    all_matches = sorted([s for s in job_skills if s.lower().strip() in all_matches_lower])
    missing = sorted([s for s in job_skills if s.lower().strip() not in all_matches_lower])
    
    return {"matched": all_matches, "missing": missing, "match_percent": (len(all_matches) / len(job_skills)) * 100}

def score_achievements_by_pattern(text: str) -> float:
    points = BULLET_POINT_PATTERN.split(text)
    if len(points) < 2: return 30.0
    scores = []
    for p in points:
        p = p.strip()
        if len(p) < 15: continue
        score = 0
        if p.split()[0].lower().rstrip('.,:;') in ACTION_VERBS: score += 4
        if METRICS_PATTERN.search(p): score += 6
        scores.append(score)
    return min(100.0, (sum(scores) / len(scores)) * 10) if scores else 30.0

def score_content_quality(text: str) -> float:
    found_essential = sum(1 for s in SECTION_KEYWORDS['essential'] if re.search(r'\b' + s + r'\b', text, re.IGNORECASE))
    found_optional = sum(1 for s in SECTION_KEYWORDS['optional'] if re.search(r'\b' + s + r'\b', text, re.IGNORECASE))
    section_score = (found_essential / len(SECTION_KEYWORDS['essential'])) * 70 + (found_optional / len(SECTION_KEYWORDS['optional'])) * 30
    word_count = len(text.split())
    length_score = min(100, (word_count / 500) * 100)
    return (section_score * 0.7) + (length_score * 0.3)

def _calculate_tfidf_similarity(text1: str, text2: str) -> float:
    try:
        tfidf = TfidfVectorizer().fit_transform([text1, text2])
        return ((tfidf * tfidf.T).A)[0,1] * 100
    except Exception:
        return 50.0

def calculate_semantic_match(resume_text: str, jd_text: str) -> float:
    #  advanced semantic match with fallback
    if not MODEL_MANAGER.is_healthy:
        logger.warning("Model unavailable. Using TF-IDF fallback for semantic match.")
        return _calculate_tfidf_similarity(resume_text, jd_text)
    embeddings = MODEL_MANAGER.model.encode([resume_text, jd_text])
    return util.cos_sim(embeddings[0], embeddings[1]).item() * 100

def score_project_relevance(resume_data: dict, jd_text: str) -> list[dict]:
    projects = resume_data.get('projects', [])
    if not projects or not MODEL_MANAGER.is_healthy:
        return projects
    jd_embedding = MODEL_MANAGER.model.encode(jd_text)
    for p in projects:
        p_text = f"{p.get('title', '')} {p.get('description', '')}"
        p_emb = MODEL_MANAGER.model.encode(p_text)
        p['relevance_score'] = round(util.cos_sim(jd_embedding, p_emb).item() * 100)
    return sorted(projects, key=lambda x: x['relevance_score'], reverse=True)

def score_experience_match(resume_data: dict, jd_text: str) -> float:
    experiences = resume_data.get('experience', [])
    if not experiences or not MODEL_MANAGER.is_healthy:
        return 30.0
    jd_embedding = MODEL_MANAGER.model.encode(jd_text)
    scores = [util.cos_sim(jd_embedding, MODEL_MANAGER.model.encode(f"{e.get('title','')} {e.get('description','')} ")).item() for e in experiences]
    return max(scores) * 100 if scores else 30.0

def calculate_ats_score(resume_text: str, job_description: str, resume_data: dict) -> dict:
    """Orchestrates the calculation of the final ATS score and its components."""
    semantic_score = calculate_semantic_match(resume_text, job_description)
    job_skills = extract_skills(job_description)
    skill_match_data = match_skills_semantically(resume_data.get('skills', []), job_skills)
    skill_score = skill_match_data['match_percent']
    achievement_score = score_achievements_by_pattern(resume_text)
    quality_score = score_content_quality(resume_text)
    experience_score = score_experience_match(resume_data, job_description)

    final_score = sum([
        semantic_score * ATS_SCORE_WEIGHTS["semantic_match"],
        skill_score * ATS_SCORE_WEIGHTS["skill_match"],
        experience_score * ATS_SCORE_WEIGHTS["experience_match"],
        achievement_score * ATS_SCORE_WEIGHTS["achievements"],
        quality_score * ATS_SCORE_WEIGHTS["content_quality"]
    ])
    
    return {
        "total_score": round(final_score),
        "breakdown": {
            "semantic_match": round(semantic_score),
            "skill_match": round(skill_score),
            "experience_match": round(experience_score),
            "achievements": round(achievement_score),
            "content_quality": round(quality_score)
        },
        "skill_gap": skill_match_data
    }

def calculate_role_suitability(resume_data: dict, job_description: str) -> dict:
    """
    Calculates how well the resume fits common full-time role categories.
    Returns scores for different role types (Frontend, Backend, Full-Stack, Data, DevOps, etc.)
    """
    role_keywords = {
        "frontend": ["frontend", "front-end", "react", "angular", "vue", "javascript", "typescript", "css", "html", "ui", "ux"],
        "backend": ["backend", "back-end", "server", "api", "database", "python", "java", "node", "php", "ruby", "sql"],
        "fullstack": ["fullstack", "full-stack", "mern", "mean", "mevn", "full stack"],
        "devops": ["devops", "aws", "azure", "gcp", "docker", "kubernetes", "ci/cd", "terraform", "infrastructure"],
        "data": ["data", "analysis", "analytics", "machine learning", "ai", "python", "r", "sql", "database", "etl"],
        "mobile": ["mobile", "ios", "android", "flutter", "react native", "swift", "kotlin"],
    }
    
    resume_text = resume_data.get('full_text', '').lower()
    scores = {}
    
    for role, keywords in role_keywords.items():
        keyword_count = sum(1 for keyword in keywords if keyword in resume_text)
        scores[role] = min(100, (keyword_count / len(keywords)) * 100)
    
    return scores

def assess_industry_fit(resume_data: dict, job_description: str) -> float:
    """
    Assesses how well the candidate's experience matches industry standards
    for the target role.
    """
    # Extract industry-specific keywords from job description
    industry_terms = extract_skills(job_description)
    
    # Check resume for these terms
    resume_skills = resume_data.get('skills', [])
    resume_text = resume_data.get('full_text', '').lower()
    
    # Calculate match score
    matched_terms = [term for term in industry_terms if term.lower() in resume_text]
    industry_fit_score = (len(matched_terms) / len(industry_terms)) * 100 if industry_terms else 0
    
    return industry_fit_score

def calculate_seniority_level(resume_data: dict) -> str:
    """
    Estimates the seniority level based on experience duration,
    leadership terms, and project complexity.
    """
    experiences = resume_data.get('experience', [])
    total_experience = 0
    
    for exp in experiences:
        duration = _calculate_experience_duration(exp)
        total_experience += duration / 12  # Convert to years
    
    # Check for leadership terms
    resume_text = resume_data.get('full_text', '').lower()
    leadership_terms = ["lead", "manager", "director", "head of", "architect", "principal", "senior"]
    leadership_score = sum(1 for term in leadership_terms if term in resume_text)
    
    # Determine seniority level
    if total_experience >= 8 or leadership_score >= 3:
        return "Senior/Principal"
    elif total_experience >= 5:
        return "Mid-Level/Senior"
    elif total_experience >= 2:
        return "Mid-Level"
    else:
        return "Entry-Level/Junior"