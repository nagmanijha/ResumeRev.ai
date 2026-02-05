# main.py

import logging
import io
from contextlib import asynccontextmanager
from starlette.concurrency import run_in_threadpool
from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Depends, Query, Security, status
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from backend.analysis_engine import (core_parser, ats_scorer, report_generator, llm_suggester)
from backend.database import engine, Base, AsyncSessionLocal
import backend.crud as crud
import backend.models as models
from backend.config import LOG_FORMAT
from backend.schemas import AnalysisResult as AnalysisResultSchema, BatchAnalysisResponse
import asyncio
import uuid
from typing import List

logger.add("logs/file_{time}.log", rotation="1 week", level="INFO", format=LOG_FORMAT)

# --- SECURITY ---
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    # For a free/local tool, we can allow empty keys or check against an env var.
    # If the user wants to secure it, they should set APP_API_KEY in .env
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    expected_key = os.getenv("APP_API_KEY")
    
    # If no key is configured in env, we default to insecure/open mode for ease of use
    if not expected_key:
        return api_key_header

    if api_key_header == expected_key:
        return api_key_header
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API Key",
    )

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
    version="6.0.0",
    lifespan=lifespan
)

# --- CORS CONFIGURATION ---
# Allow requests from any origin (Vercel, Localhost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

from fastapi.staticfiles import StaticFiles
from pathlib import Path

# Get the project root directory (parent of backend folder)
PROJECT_ROOT = Path(__file__).parent.parent

# Mount static files for frontend
app.mount("/static/fonts", StaticFiles(directory=PROJECT_ROOT / "fonts"), name="fonts")
app.mount("/static", StaticFiles(directory=PROJECT_ROOT / "frontend"), name="static")

@app.get("/", include_in_schema=False)
async def root():
    """Serve the frontend index.html"""
    return FileResponse(PROJECT_ROOT / "frontend" / "index.html")


@app.post("/analyze/", tags=["Core Functionality"])
async def analyze_resume(
    job_description: str = Form(..., min_length=50),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    api_key: str = Security(get_api_key) 
):
    try:
        # Validate file size (e.g., 10MB limit)
        file.file.seek(0, 2)
        file_size = file.file.tell()
        await file.seek(0)
        
        if file_size > 10 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="File too large. Maximum size is 10MB.")

        file_content = await file.read()
        
        logger.info(f"Starting async analysis for file: {file.filename}")

        # --- NON-BLOCKING EXECUTION WRAPPER ---
        # CPU-bound tasks (parsing, scoring) must be run in a separate thread 
        # to ensure the main event loop stays responsive for other requests.
        def _process_analysis():
            parsed_data = core_parser.parse_resume_details(file_content, file.filename)
            scored_projects = ats_scorer.score_project_relevance(parsed_data, job_description)
            parsed_data['projects'] = scored_projects 
            ats_score_data = ats_scorer.calculate_ats_score(parsed_data['full_text'], job_description, parsed_data)
            skill_levels = ats_scorer.rate_skill_levels(parsed_data)

            role_suitability = ats_scorer.calculate_role_suitability(parsed_data, job_description)
            industry_fit = ats_scorer.assess_industry_fit(parsed_data, job_description)
            seniority_level = ats_scorer.calculate_seniority_level(parsed_data)
            
            return parsed_data, ats_score_data, skill_levels, role_suitability, industry_fit, seniority_level

        # Run CPU-bound task in threadpool
        parsed_data, ats_score_data, skill_levels, role_suitability, industry_fit, seniority_level = await run_in_threadpool(_process_analysis)

        # IO-bound/Async tasks can run normally
        suggestion_data = {
            "ats_score": ats_score_data, 
            "skill_gap": ats_score_data['skill_gap'],
            "role_suitability": role_suitability,
            "industry_fit": industry_fit,
            "seniority_level": seniority_level
        }
        suggestions = await run_in_threadpool(llm_suggester.get_llm_suggestions, suggestion_data)
        
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

    except HTTPException as he:
        raise he
    except ValueError as e:
        logger.warning(f"Validation Error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in /analyze/ endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")

# --- BATCH PROCESSING (V2) ---

def _analyze_single_resume_sync(file_content: bytes, filename: str, job_description: str) -> dict | None:
    """
    Sync helper for batch processing. 
    Skips LLM suggestions to ensure speed but runs full ATS/Scoring.
    """
    try:
        parsed_data = core_parser.parse_resume_details(file_content, filename)
        
        # Calculate scores
        # Project Relevance
        scored_projects = ats_scorer.score_project_relevance(parsed_data, job_description)
        parsed_data['projects'] = scored_projects
        
        # ATS Score (Unified V2 Formula)
        ats_score_data = ats_scorer.calculate_ats_score(parsed_data['full_text'], job_description, parsed_data)
        
        # Check missing skills (Critical for recruiters)
        missing_skills = ats_score_data['skill_gap']['missing']
        
        return {
            "filename": filename,
            "scores": ats_score_data, # Contains breakdown
            "missing_skills": missing_skills
        }
    except Exception as e:
        logger.error(f"Failed to process {filename} in batch: {e}")
        return None

@app.post("/analyze-batch/", response_model=BatchAnalysisResponse, tags=["Batch Processing"])
async def analyze_batch(
    job_description: str = Form(..., min_length=50),
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    api_key: str = Security(get_api_key)
):
    batch_id = str(uuid.uuid4())
    logger.info(f"Starting batch analysis {batch_id} for {len(files)} files")

    # Limit concurrency to 5 parallel tasks to prevent OOM
    sem = asyncio.Semaphore(5)

    async def _process_safe(file: UploadFile):
        async with sem:
            try:
                # Basic validation
                file.file.seek(0, 2)
                size = file.file.tell()
                await file.seek(0)
                if size > 10 * 1024 * 1024: # 10MB limit
                    logger.warning(f"File {file.filename} skipped (Too Large)")
                    return None
                    
                content = await file.read()
                return await run_in_threadpool(_analyze_single_resume_sync, content, file.filename, job_description)
            except Exception as e:
                logger.error(f"Async worker failed for {file.filename}: {e}")
                return None

    # Execute all tasks
    tasks = [_process_safe(f) for f in files]
    results = await asyncio.gather(*tasks)
    
    # Filter failed results
    valid_results = [r for r in results if r is not None]
    
    # Rank by Total Score (Descending)
    valid_results.sort(key=lambda x: x['scores']['total_score'], reverse=True)
    
    # Format for response
    batch_items = []
    for rank, item in enumerate(valid_results, 1):
        batch_items.append({
            "filename": item['filename'],
            "rank": rank,
            "scores": {
                "total": item['scores']['total_score'],
                "skills": item['scores']['breakdown']['skill_match'], 
                "experience": item['scores']['breakdown']['experience_match']
            },
            "missing_skills": item['missing_skills'][:5] # Top 5 missing
        })
        
        # Optional: Save to DB efficiently? 
        # For V2 MVP, we return JSON. Future: Bulk Insert.

    return {
        "batch_id": batch_id,
        "processed_count": len(valid_results),
        "results": batch_items
    }
    

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