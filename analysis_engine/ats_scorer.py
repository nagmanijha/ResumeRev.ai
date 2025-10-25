import logging
from .model_manager import ModelManager
from .skill_matcher import SkillMatcher
from .experience_analyzer import ExperienceAnalyzer
from .content_scorer import ContentScorer
from .semantic_matcher import SemanticMatcher
from .role_analyzer import RoleAnalyzer
from config import ATS_SCORE_WEIGHTS

logger = logging.getLogger(__name__)


class ATSscorer:
    def __init__(self):
        self.model_manager = ModelManager()
        self.skill_matcher = SkillMatcher(self.model_manager)
        self.experience_analyzer = ExperienceAnalyzer()
        self.content_scorer = ContentScorer()
        self.semantic_matcher = SemanticMatcher(self.model_manager)
        self.role_analyzer = RoleAnalyzer()

    def calculate_ats_score(self, resume_text, job_description, resume_data):
        try:
            semantic_score = self.semantic_matcher.calculate_semantic_match(resume_text, job_description)

            from .core_parser import extract_skills
            job_skills = extract_skills(job_description)
            skill_match_data = self.skill_matcher.match_skills(resume_data.get('skills', []), job_skills)
            skill_score = skill_match_data['match_percent']

            achievement_score = self.experience_analyzer.score_achievements(resume_text)
            quality_score = self.content_scorer.score_content_quality(resume_text)
            experience_score = self.semantic_matcher.score_experience_match(resume_data, job_description)

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
        except Exception as e:
            logger.error(f"Error calculating ATS score: {e}")
            # Return a minimal score object to prevent complete failure
            return {
                "total_score": 0,
                "breakdown": {
                    "semantic_match": 0,
                    "skill_match": 0,
                    "experience_match": 0,
                    "achievements": 0,
                    "content_quality": 0
                },
                "skill_gap": {
                    "matched": [],
                    "missing": [],
                    "match_percent": 0
                }
            }

    def rate_skill_levels(self, resume_data):
        return self.experience_analyzer.rate_skill_levels(resume_data)

    def score_project_relevance(self, resume_data, jd_text):
        return self.semantic_matcher.score_project_relevance(resume_data, jd_text)

    def calculate_role_suitability(self, resume_data, job_description):
        return self.role_analyzer.calculate_role_suitability(resume_data, job_description)

    def assess_industry_fit(self, resume_data, job_description):
        return self.role_analyzer.assess_industry_fit(resume_data, job_description)

    def calculate_seniority_level(self, resume_data):
        return self.role_analyzer.calculate_seniority_level(resume_data, self.experience_analyzer)


# Global instance for backward compatibility
def calculate_ats_score(resume_text, job_description, resume_data):
    scorer = ATSscorer()
    return scorer.calculate_ats_score(resume_text, job_description, resume_data)


def rate_skill_levels(resume_data):
    scorer = ATSscorer()
    return scorer.rate_skill_levels(resume_data)


def score_project_relevance(resume_data, jd_text):
    scorer = ATSscorer()
    return scorer.score_project_relevance(resume_data, jd_text)


def calculate_role_suitability(resume_data, job_description):
    scorer = ATSscorer()
    return scorer.calculate_role_suitability(resume_data, job_description)


def assess_industry_fit(resume_data, job_description):
    scorer = ATSscorer()
    return scorer.assess_industry_fit(resume_data, job_description)


def calculate_seniority_level(resume_data):
    scorer = ATSscorer()
    return scorer.calculate_seniority_level(resume_data)