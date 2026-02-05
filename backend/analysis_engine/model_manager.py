import logging
from sentence_transformers import SentenceTransformer, util
from backend.config import MODEL_NAME

logger = logging.getLogger(__name__)


class ModelManager:
    _instance = None
    _model = None
    _is_healthy = False

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
    def model(self):
        return self._model

    @property
    def is_healthy(self):
        return self._is_healthy


# Global instance
MODEL_MANAGER = ModelManager()