# crud.py
# Handles all Create, Read, Update, Delete (CRUD) operations for the database.

import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

import models

logger = logging.getLogger(__name__)

async def get_or_create_skill(db: AsyncSession, skill_name: str) -> models.Skill:
    """Gets a skill by name or creates it if it doesn't exist."""
    skill_name_lower = skill_name.lower().strip()
    result = await db.execute(select(models.Skill).filter(models.Skill.name == skill_name_lower))
    skill = result.scalar_one_or_none()
    if not skill:
        skill = models.Skill(name=skill_name_lower)
        db.add(skill)
        await db.flush() # Flush to get the ID without committing the full transaction
    return skill

async def create_analysis_result(db: AsyncSession, analysis_data: dict) -> models.AnalysisResult:
    """Creates a new analysis result with proper transaction handling."""
    try:
        parsed_info = analysis_data.get('parsed_data', {})
        score = float(analysis_data.get('ats_score', {}).get('total_score', 0.0))

        db_result = models.AnalysisResult(
            filename=parsed_info.get('filename'),
            name=parsed_info.get('name'),
            email=parsed_info.get('contact', {}).get('email'),
            phone=parsed_info.get('contact', {}).get('phone'),
            total_score=score
        )

        skill_names = parsed_info.get('skills', [])
        for skill_name in skill_names:
            skill = await get_or_create_skill(db, skill_name)
            db_result.skills.append(skill)

        db.add(db_result)
        await db.commit()
        await db.refresh(db_result)
        logger.info(f"Successfully created analysis result for {db_result.filename}")
        return db_result
    except Exception as e:
        logger.error(f"Database error during result creation: {e}", exc_info=True)
        await db.rollback()
        raise

async def get_all_results(db: AsyncSession, skip: int = 0, limit: int = 20):
    """
    Retrieves analysis results with pagination.
    FIX: Added pagination and optimized query loading.
    """
    query = (
        select(models.AnalysisResult)
        .order_by(models.AnalysisResult.timestamp.desc())
        .offset(skip)
        .limit(limit)
        .options(selectinload(models.AnalysisResult.skills)) # Eager load skills to prevent N+1 queries
    )
    result = await db.execute(query)
    return result.scalars().all()

# Add this function to crud.py

async def get_result_by_id(db: AsyncSession, analysis_id: int) -> models.AnalysisResult | None:
    """Fetches a single analysis result by its ID."""
    query = (
        select(models.AnalysisResult)
        .where(models.AnalysisResult.id == analysis_id)
        .options(selectinload(models.AnalysisResult.skills))
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()