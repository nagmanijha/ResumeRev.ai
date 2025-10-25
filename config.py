# config.py

# --- SCORING WEIGHTS ---
ATS_SCORE_WEIGHTS = {
    "semantic_match": 0.30,
    "skill_match": 0.30,
    "experience_match": 0.25,
    "achievements": 0.10,
    "content_quality": 0.05,
}

# --- THRESHOLDS ---
SEMANTIC_SKILL_MATCH_THRESHOLD = 0.7
FUZZY_SKILL_MATCH_THRESHOLD = 85 
MAX_SKILLS_TO_MATCH = 50 

# --- MODEL CONFIG ---
MODEL_NAME = 'all-MiniLM-L6-v2'

# --- KEYWORD LISTS ---
ACTION_VERBS = {
    'achieved', 'accelerated', 'accomplished', 'architected', 'automated', 
    'built', 'created', 'delivered', 'designed', 'developed', 'engineered', 
    'enhanced', 'executed', 'generated', 'implemented', 'improved', 
    'increased', 'initiated', 'launched', 'led', 'managed', 'optimized', 
    'orchestrated', 'pioneered', 'produced', 'reduced', 'saved', 'solved', 
    'spearheaded', 'streamlined'
}

SECTION_KEYWORDS = {
    "essential": ['experience', 'education', 'skills'],
    "optional": ['summary', 'projects', 'certifications', 'awards']
}

LOG_LEVEL = "INFO"
LOG_FORMAT = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"