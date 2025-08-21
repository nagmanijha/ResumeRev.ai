# schemas.py

from pydantic import BaseModel, Field
from datetime import datetime
from typing import List

# This Pydantic model represents a Skill for the API response
class Skill(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True # Tells Pydantic to read data from ORM model attributes

# This is the main Pydantic model for the AnalysisResult
class AnalysisResult(BaseModel):
    id: int
    filename: str | None = None
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    total_score: float = Field(..., ge=0, le=100) # Add validation: score >= 0 and <= 100
    timestamp: datetime
    skills: List[Skill] = [] # A list of Skill objects

    class Config:
        # FIX: This is the crucial part that allows Pydantic to work with SQLAlchemy models.
        from_attributes = True