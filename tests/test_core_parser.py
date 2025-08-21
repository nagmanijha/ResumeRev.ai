import pytest
from analysis_engine import core_parser

def test_extract_skills_found():
    text = "My skills include Python, Java, and Machine Learning."
    expected = {"python", "java", "machine learning"}
    assert set(core_parser.extract_skills(text)) == expected

def test_extract_skills_not_found():
    text = "I am a project manager."
    assert core_parser.extract_skills(text) == []

def test_extract_contact_info():
    text = "Contact me at john.doe@email.com or on 123-456-7890."
    expected = {"email": "john.doe@email.com", "phone": "123-456-7890"}
    assert core_parser.extract_contact_info(text) == expected