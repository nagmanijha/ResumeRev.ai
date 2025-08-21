# main.py

import logging
import io
from contextlib import asynccontextmanager
from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Depends, Query
from fastapi.responses import JSONResponse, Response, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from analysis_engine import (core_parser, ats_scorer, report_generator, llm_suggester)
from database import engine, Base, AsyncSessionLocal
import crud
import models
from config import LOG_FORMAT
from schemas import AnalysisResult as AnalysisResultSchema

logger.add("logs/file_{time}.log", rotation="1 week", level="INFO", format=LOG_FORMAT)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("NLP models loaded and database tables checked/created.")
    yield
    logger.info("Application shutdown...")

app = FastAPI(
    title = "ResumeRev.ai",
    description = "AI-driven resume intelligence for job seekers and hiring platforms. Instantly analyze, score, and optimize resumes for any job role with market-aligned insights.",
    version="5.0.0",
    lifespan=lifespan
)

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=FileResponse, include_in_schema=False)

async def root():
    return "static/index.html"

@app.post("/analyze/", tags=["Core Functionality"])
async def analyze_resume(
    job_description: str = Form(..., min_length=50),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    try:
        file_content = await file.read()
        
        logger.info(f"Starting analysis for file: {file.filename}")
        parsed_data = core_parser.parse_resume_details(file_content, file.filename)
        scored_projects = ats_scorer.score_project_relevance(parsed_data, job_description)
        parsed_data['projects'] = scored_projects 
        ats_score_data = ats_scorer.calculate_ats_score(parsed_data['full_text'], job_description, parsed_data)
        skill_levels = ats_scorer.rate_skill_levels(parsed_data)

        role_suitability = ats_scorer.calculate_role_suitability(parsed_data, job_description)
        industry_fit = ats_scorer.assess_industry_fit(parsed_data, job_description)
        seniority_level = ats_scorer.calculate_seniority_level(parsed_data)

        suggestion_data = {
            "ats_score": ats_score_data, 
            "skill_gap": ats_score_data['skill_gap'],
            "role_suitability": role_suitability,
            "industry_fit": industry_fit,
            "seniority_level": seniority_level
        }
        suggestions = llm_suggester.get_llm_suggestions(suggestion_data)
        
        full_analysis = {
            "parsed_data": parsed_data,
            "ats_score": ats_score_data,
            "skill_levels": skill_levels,
            "suggestions": suggestions,
            "role_suitability": role_suitability,
            "industry_fit": industry_fit,
            "seniority_level": seniority_level
        }

        db_result = await crud.create_analysis_result(db, full_analysis)
        full_analysis["analysis_id"] = db_result.id

        logger.info(f"Analysis complete for file: {file.filename}")
        return JSONResponse(content=full_analysis)
    except ValueError as e:
        logger.warning(f"Validation Error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in /analyze/ endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal server error occurred.")
    

@app.get("/results/", response_model=list[AnalysisResultSchema], tags=["Results History"])
async def get_results(
    db: AsyncSession = Depends(get_db), 
    skip: int = Query(0, ge=0), 
    limit: int = Query(20, ge=1, le=100)
):
    return await crud.get_all_results(db, skip=skip, limit=limit)


@app.post("/download-report/", tags=["Reporting"])
async def download_report(
    job_description: str = Form(...),
    file: UploadFile = File(...)
):
    """
    Generates and returns a complete PDF report on-the-fly.
    This is computationally intensive but ensures all data is present.
    """
    try:
        file_content = await file.read()
        
        parsed_data = core_parser.parse_resume_details(file_content, file.filename)
        ats_score_data = ats_scorer.calculate_ats_score(parsed_data['full_text'], job_description, parsed_data)
        skill_levels = ats_scorer.rate_skill_levels(parsed_data)
        suggestions = llm_suggester.get_llm_suggestions({"ats_score": ats_score_data, "skill_gap": ats_score_data['skill_gap']})
        
        # Combine into a single, complete dictionary for the report generator
        full_analysis_data = {
            "parsed_data": parsed_data,
            "ats_score": ats_score_data,
            "skill_levels": skill_levels,
            "suggestions": suggestions
        }
        
        pdf_bytes = report_generator.generate_pdf_report(full_analysis_data)
        
        return StreamingResponse(io.BytesIO(pdf_bytes), media_type="application/pdf", 
            headers={"Content-Disposition": f"attachment;filename=ResumeAnalysis_{file.filename}.pdf"})
            
    except Exception as e:
        logger.error(f"Error in /download-report/ endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal server error occurred while generating the report.")