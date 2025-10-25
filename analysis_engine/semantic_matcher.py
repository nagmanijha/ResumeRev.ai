import logging
from sklearn.feature_extraction.text import TfidfVectorizer
from .model_manager import MODEL_MANAGER
from sentence_transformers import util

logger = logging.getLogger(__name__)


class SemanticMatcher:
    def __init__(self, model_manager):
        self.model_manager = model_manager

    def calculate_semantic_match(self, resume_text, jd_text):
        if not self.model_manager.is_healthy:
            logger.warning("Model unavailable. Using TF-IDF fallback for semantic match.")
            return self._calculate_tfidf_similarity(resume_text, jd_text)

        try:
            embeddings = self.model_manager.model.encode([resume_text, jd_text])
            return util.cos_sim(embeddings[0], embeddings[1]).item() * 100
        except Exception as e:
            logger.error(f"Error in semantic matching: {e}")
            return self._calculate_tfidf_similarity(resume_text, jd_text)

    def _calculate_tfidf_similarity(self, text1, text2):
        try:
            tfidf = TfidfVectorizer().fit_transform([text1, text2])
            return ((tfidf * tfidf.T).A)[0, 1] * 100
        except Exception as e:
            logger.error(f"Error in TF-IDF calculation: {e}")
            return 50.0

    def score_experience_match(self, resume_data, jd_text):
        experiences = resume_data.get('experience', [])
        if not experiences or not self.model_manager.is_healthy:
            return 30.0

        try:
            jd_embedding = self.model_manager.model.encode(jd_text)
            scores = [
                util.cos_sim(
                    jd_embedding,
                    self.model_manager.model.encode(f"{e.get('title', '')} {e.get('description', '')}")
                ).item()
                for e in experiences
            ]
            return max(scores) * 100 if scores else 30.0
        except Exception as e:
            logger.error(f"Error in experience matching: {e}")
            return 30.0

    def score_project_relevance(self, resume_data, jd_text):
        projects = resume_data.get('projects', [])
        if not projects or not self.model_manager.is_healthy:
            return projects

        try:
            jd_embedding = self.model_manager.model.encode(jd_text)
            for p in projects:
                p_text = f"{p.get('title', '')} {p.get('description', '')}"
                p_emb = self.model_manager.model.encode(p_text)
                p['relevance_score'] = round(util.cos_sim(jd_embedding, p_emb).item() * 100)
            return sorted(projects, key=lambda x: x['relevance_score'], reverse=True)
        except Exception as e:
            logger.error(f"Error in project relevance scoring: {e}")
            return projects