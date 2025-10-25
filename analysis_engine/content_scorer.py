import re
import logging
from config import SECTION_KEYWORDS

logger = logging.getLogger(__name__)


class ContentScorer:
    def score_content_quality(self, text):
        found_essential = sum(
            1 for s in SECTION_KEYWORDS['essential']
            if re.search(r'\b' + s + r'\b', text, re.IGNORECASE)
        )
        found_optional = sum(
            1 for s in SECTION_KEYWORDS['optional']
            if re.search(r'\b' + s + r'\b', text, re.IGNORECASE)
        )

        section_score = (
                (found_essential / len(SECTION_KEYWORDS['essential'])) * 70 +
                (found_optional / len(SECTION_KEYWORDS['optional'])) * 30
        )

        word_count = len(text.split())
        length_score = min(100, (word_count / 500) * 100)

        return (section_score * 0.7) + (length_score * 0.3)