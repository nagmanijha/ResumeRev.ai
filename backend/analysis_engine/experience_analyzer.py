import re
import logging
from datetime import datetime
from backend.config import ACTION_VERBS

logger = logging.getLogger(__name__)


class ExperienceAnalyzer:
    BULLET_POINT_PATTERN = re.compile(r'\n\s*[\*•\-]\s*')
    METRICS_PATTERN = re.compile(r'\b(\d+%?|\$\d+(?:,\d+)*(?:\.\d+)?\%?|\d+(?:\.\d+)?x)\b', re.IGNORECASE)

    def calculate_experience_duration(self, experience):
        start_str, end_str = experience.get('start_date', ''), experience.get('end_date', 'Present')
        try:
            start_date = datetime.strptime(start_str, '%Y-%m-%d')
            end_date = datetime.now() if end_str == 'Present' else datetime.strptime(end_str, '%Y-%m-%d')
            return max(1, (end_date - start_date).days / 30.44)
        except (ValueError, TypeError):
            return 6.0  # Default to 6 months if parsing fails

    def score_achievements(self, text):
        points = self.BULLET_POINT_PATTERN.split(text)
        if len(points) < 2:
            return 30.0

        scores = []
        for p in points:
            p = p.strip()
            if len(p) < 15:
                continue

            score = 0
            if p.split()[0].lower().rstrip('.,:;') in ACTION_VERBS:
                score += 4
            if self.METRICS_PATTERN.search(p):
                score += 6
            scores.append(score)

        return min(100.0, (sum(scores) / len(scores)) * 10) if scores else 30.0

    def rate_skill_levels(self, resume_data):
        skills = resume_data.get('skills', [])
        skill_experience = {
            skill.lower(): sum(1 for p in resume_data.get('projects', [])
                               if skill in p.get('technologies', []))
            for skill in skills
        }

        for exp in resume_data.get('experience', []):
            duration_years = self.calculate_experience_duration(exp) / 12
            for tech in exp.get('technologies', []):
                if tech.lower() in skill_experience:
                    skill_experience[tech.lower()] += duration_years

        skill_levels = {}
        for skill in skills:
            exp_score = skill_experience.get(skill.lower(), 0)
            if exp_score >= 3:
                level = 'Expert'
            elif exp_score >= 1.5:
                level = 'Advanced'
            elif exp_score > 0:
                level = 'Intermediate'
            else:
                level = 'Beginner'
            skill_levels[skill] = level

        return skill_levels