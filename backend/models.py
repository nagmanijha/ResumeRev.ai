# models.py
# Defines the database schema using SQLAlchemy ORM.

from sqlalchemy import (Column, Integer, String, Float, DateTime, ForeignKey, Table,
                        UniqueConstraint, JSON)
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
import re

from backend.database import Base

analysis_skill_association = Table(
    'analysis_skill_association',
    Base.metadata,
    Column('analysis_id', Integer, ForeignKey('analysis_results.id'), primary_key=True),
    Column('skill_id', Integer, ForeignKey('skills.id'), primary_key=True)
)

class Skill(Base):
    __tablename__ = "skills"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)

class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    name = Column(String)
    email = Column(String, index=True, unique=False, nullable=True) # Set unique=True if you expect one analysis per email
    phone = Column(String)
    total_score = Column(Float, nullable=False)
    
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    details = Column(JSON, nullable=True) # Store full analysis JSON (suggestions, projects, etc.)

    skills = relationship("Skill", secondary=analysis_skill_association, backref="analyses")

    @validates('email')
    def validate_email(self, key, address):
        if address and not re.match(r"[^@]+@[^@]+\.[^@]+", address):
            raise ValueError("Invalid email address format")
        return address

    @validates('total_score')
    def validate_score(self, key, score):
        if not 0 <= score <= 100:
            raise ValueError("Score must be between 0 and 100")
        return score