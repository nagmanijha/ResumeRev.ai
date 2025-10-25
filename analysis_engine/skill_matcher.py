import logging
from rapidfuzz import process, fuzz
from .model_manager import MODEL_MANAGER
from config import SEMANTIC_SKILL_MATCH_THRESHOLD, FUZZY_SKILL_MATCH_THRESHOLD, MAX_SKILLS_TO_MATCH

logger = logging.getLogger(__name__)


class SkillMatcher:
    def __init__(self, model_manager):
        self.model_manager = model_manager

    def match_skills(self, resume_skills, job_skills):
        if not job_skills:
            return {"matched": resume_skills, "missing": [], "match_percent": 100}
        if not resume_skills:
            return {"matched": [], "missing": job_skills, "match_percent": 0}

        try:
            resume_lower = [s.lower().strip() for s in resume_skills]
            job_lower = [s.lower().strip() for s in job_skills]

            # Exact matches
            exact_matches = set(s for s in job_lower if s in resume_lower)

            # Find remaining skills to match
            rem_job = [s for s in job_lower if s not in exact_matches]
            rem_resume = [s for s in resume_lower if s not in exact_matches]

            # Fuzzy matches
            fuzzy_matches = self._find_fuzzy_matches(rem_job, rem_resume)

            # Semantic matches
            semantic_matches = self._find_semantic_matches(
                [s for s in rem_job if s not in fuzzy_matches],
                [s for s in rem_resume if s not in fuzzy_matches]
            )

            # Combine all matches
            all_matches_lower = exact_matches.union(fuzzy_matches).union(semantic_matches)
            all_matches = sorted([s for s in job_skills if s.lower().strip() in all_matches_lower])
            missing = sorted([s for s in job_skills if s.lower().strip() not in all_matches_lower])

            return {
                "matched": all_matches,
                "missing": missing,
                "match_percent": (len(all_matches) / len(job_skills)) * 100
            }
        except Exception as e:
            logger.error(f"Error in skill matching: {e}")
            # Fallback to simple matching
            matched = [s for s in job_skills if s.lower() in [rs.lower() for rs in resume_skills]]
            return {
                "matched": matched,
                "missing": [s for s in job_skills if s not in matched],
                "match_percent": (len(matched) / len(job_skills)) * 100 if job_skills else 0
            }

    def _find_fuzzy_matches(self, job_skills, resume_skills):
        fuzzy_matches = set()
        if job_skills and resume_skills:
            for js in job_skills:
                match = process.extractOne(
                    js, resume_skills,
                    scorer=fuzz.token_set_ratio,
                    score_cutoff=FUZZY_SKILL_MATCH_THRESHOLD
                )
                if match:
                    fuzzy_matches.add(js)
                    resume_skills.remove(match[0])
        return fuzzy_matches

    def _find_semantic_matches(self, job_skills, resume_skills):
        semantic_matches = set()
        if self.model_manager.is_healthy and job_skills and resume_skills:
            try:
                job_emb = self.model_manager.model.encode(job_skills[:MAX_SKILLS_TO_MATCH])
                res_emb = self.model_manager.model.encode(resume_skills[:MAX_SKILLS_TO_MATCH])
                scores = util.cos_sim(job_emb, res_emb)

                for i in range(len(job_skills[:MAX_SKILLS_TO_MATCH])):
                    if scores[i].max() > SEMANTIC_SKILL_MATCH_THRESHOLD:
                        semantic_matches.add(job_skills[i])
            except Exception as e:
                logger.error(f"Error in semantic matching: {e}")
        return semantic_matches