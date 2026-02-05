# analysis_engine/llm_suggester.py

import os
import json
import logging
from dotenv import load_dotenv # FIX: Add this import
from tenacity import retry, stop_after_attempt, wait_random_exponential
import google.generativeai as genai

from pathlib import Path

# Load .env from backend directory or root
current_dir = Path(__file__).resolve().parent
# Try backend/.env (parent of analysis_engine is backend)
env_path = current_dir.parent / '.env'
if not env_path.exists():
    # Try root/.env (parent of backend)
    env_path = current_dir.parent.parent / '.env'

load_dotenv(dotenv_path=env_path)

logger = logging.getLogger(__name__)

API_KEY = os.getenv("GEMINI_API_KEY")

# DEBUG LOGGING
if API_KEY:
    logger.info(f"DEBUG: API Key found (Starts with {API_KEY[:4]}...)")
else:
    logger.warning(f"DEBUG: API Key NOT found. Checked path: {env_path}")

if not API_KEY:
    logger.warning("GEMINI_API_KEY environment variable not set. LLM suggestions will be disabled.")
    # We don't need to configure a dummy key, just check the API_KEY variable later.
else:
    genai.configure(api_key=API_KEY)

def build_prompt(data: dict) -> str:
    """Constructs the prompt for the LLM based on analysis data."""
    ats_score = data['ats_score']['total_score']
    missing_skills = data['skill_gap']['missing']
    achievements_score = data['ats_score']['breakdown'].get('achievements', 50)
    
    # Use a default skill if the list is empty to prevent errors
    example_skill = missing_skills[0] if missing_skills else "a required skill like Python or AWS"

    return f"""
    You are an expert career coach and professional resume writer providing feedback on a resume for a specific job.
    The resume received an overall ATS score of {ats_score}/100.

    The analysis revealed the following:
    - Key skills required by the job but missing from the resume: {', '.join(missing_skills) if missing_skills else 'None'}
    - A score for quantifiable, action-oriented achievements: {achievements_score}/100

    Based ONLY on this data, provide 3-4 concise, highly actionable suggestions for the candidate.
    Your suggestions must be profound and specific. Instead of generic advice, provide concrete examples.
    Focus on how to integrate missing skills and how to rephrase experience using the "[Action Verb] [Metric] [Result]" framework.

    Example of a weak suggestion: "Add more skills."
    Example of a strong suggestion: "Weave '{example_skill}' into your project descriptions. For instance, instead of 'worked on the backend', try 'Architected a new backend service using {example_skill} to handle 10,000 requests per second'."
    Example of another strong suggestion: "Rephrase your accomplishments to show impact. Instead of 'Responsible for the database', try 'Optimized SQL queries which reduced report generation time by 30%'."

    Format the output as a valid JSON array of strings. Example: ["Suggestion 1", "Suggestion 2"].
    Do not add any other text, explanation, or markdown formatting.
    """

def clean_response(text: str) -> list[str]:
    """Cleans and parses the model's response into a list of suggestions."""
    # This defensive parsing is safer than eval()
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    suggestions = json.loads(cleaned)
    if not isinstance(suggestions, list) or not all(isinstance(s, str) for s in suggestions):
        raise ValueError("AI response is not a valid list of strings.")
    return suggestions

def fallback_suggestions() -> list[str]:
    """Returns static fallback suggestions if the LLM fails."""
    return [
        "Strengthen your resume by adding more metrics to your experience section.",
        "Ensure your skills section closely matches the most important requirements in the job description.",
        "Use strong action verbs to begin each bullet point in your work history.",
        "Consider adding a professional summary at the top of your resume to highlight your key strengths."
    ]

@retry(wait=wait_random_exponential(min=1, max=10), stop=stop_after_attempt(1))
def get_llm_suggestions(analysis_data: dict) -> list[str]:
    """Generates actionable LLM suggestions from resume analysis data."""
    if not API_KEY:
        return fallback_suggestions()

    try:
        prompt = build_prompt(analysis_data)
        # Use a faster, lighter model and add timeout
        model = genai.GenerativeModel('models/gemini-1.5-flash')
        response = model.generate_content(prompt, request_options={'timeout': 10})
        return clean_response(response.text)
    except Exception as e:
        logger.error(f"Failed to get or parse LLM suggestions: {e}", exc_info=True)
        return fallback_suggestions()