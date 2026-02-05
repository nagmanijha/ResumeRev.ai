import logging
from .core_parser import extract_skills

logger = logging.getLogger(__name__)


class RoleAnalyzer:
    def __init__(self):
        self.role_keywords = {
            "frontend": ["frontend", "front-end", "react", "angular", "vue", "javascript", "typescript", "css", "html",
                         "ui", "ux"],
            "backend": ["backend", "back-end", "server", "api", "database", "python", "java", "node", "php", "ruby",
                        "sql"],
            "fullstack": ["fullstack", "full-stack", "mern", "mean", "mevn", "full stack"],
            "devops": ["devops", "aws", "azure", "gcp", "docker", "kubernetes", "ci/cd", "terraform", "infrastructure"],
            "data": ["data", "analysis", "analytics", "machine learning", "ai", "python", "r", "sql", "database",
                     "etl"],
            "mobile": ["mobile", "ios", "android", "flutter", "react native", "swift", "kotlin"],
        }

    def calculate_role_suitability(self, resume_data, job_description):
        resume_text = resume_data.get('full_text', '').lower()
        scores = {}

        for role, keywords in self.role_keywords.items():
            keyword_count = sum(1 for keyword in keywords if keyword in resume_text)
            scores[role] = min(100, (keyword_count / len(keywords)) * 100)

        return scores

    def assess_industry_fit(self, resume_data, job_description):
        industry_terms = extract_skills(job_description)
        resume_text = resume_data.get('full_text', '').lower()

        matched_terms = [term for term in industry_terms if term.lower() in resume_text]
        industry_fit_score = (len(matched_terms) / len(industry_terms)) * 100 if industry_terms else 0

        return industry_fit_score

    def calculate_seniority_level(self, resume_data, experience_analyzer):
        experiences = resume_data.get('experience', [])
        total_experience = 0

        for exp in experiences:
            duration = experience_analyzer.calculate_experience_duration(exp)
            total_experience += duration / 12  # Convert to years

        resume_text = resume_data.get('full_text', '').lower()
        leadership_terms = ["lead", "manager", "director", "head of", "architect", "principal", "senior"]
        leadership_score = sum(1 for term in leadership_terms if term in resume_text)

        if total_experience >= 8 or leadership_score >= 3:
            return "Senior/Principal"
        elif total_experience >= 5:
            return "Mid-Level/Senior"
        elif total_experience >= 2:
            return "Mid-Level"
        else:
            return "Entry-Level/Junior"