
# 🚀 ResumeRev.ai

### Don't just apply. Get hired. Your personal AI career coach for crafting the perfect, job-winning resume.

**ResumeRev.ai** is a production-grade web application that provides a deep, AI-driven analysis of your resume against a specific job description. It moves beyond simple keyword matching to offer a comprehensive, multi-faceted evaluation, helping you understand precisely how a recruiter and an ATS (Applicant Tracking System) will perceive your application.

-----

## ✨ Key Features

  * 🧠 **Multi-Factor ATS Scoring:** Get a detailed score (0-100) based on a weighted analysis of semantic match, skill gaps, experience relevance, quantifiable achievements, and content quality.

  * 🎯 **Role-Specific Evaluation:** The AI engine intelligently detects the target role (e.g., Backend, Frontend, Data) and dynamically adjusts its scoring rubric to prioritize what matters most for that position.

  * 🤖 **Recruiter Simulation:** A "30-second scan" feature powered by a Large Language Model (LLM) that gives you a first-impression summary, identifying immediate strengths and areas that lack clarity, just like a busy recruiter would.

  * 📊 **Advanced Project & Experience Analysis:** Each project and past job on your resume is individually scored for its relevance to the job description, using semantic embeddings to understand the context of your work.

  * 📄 **Professional PDF Reporting:** Download a clean, minimalist, and professional PDF summary of your full analysis, perfect for sharing or personal review.

-----

## 🛠️ Tech Stack

  * **Backend:** **FastAPI**, **SQLAlchemy**, **Pydantic**
  * **Frontend:** **Tailwind CSS**, Vanilla **JavaScript**
  * **AI / ML:**
      * **LLM:** **Google Gemini**
      * **Embeddings:** **Sentence-Transformers**
      * **NLP:** **spaCy**, **TextBlob**
  * **Database:** **SQLite** (with schema ready for **PostgreSQL**)
  * **PDF Generation:** **FPDF2**

-----

## 🏗️ System Architecture

The application follows a modern, modular, and scalable design pattern:

1.  **Frontend (Client):** A user submits their resume and a job description via the Tailwind CSS interface.
2.  **API (FastAPI):** The request hits a specific endpoint (e.g., `/analyze/`).
3.  **Core Parser:** The system first extracts and structures all text, skills, projects, and experiences from the resume file.
4.  **Analysis Engine:** The structured data is passed to a suite of specialized modules:
      * `ats_scorer.py`: Calculates the multi-factor scores.
      * `role_detector.py`: Determines the job profile.
      * `project_scorer.py`: Scores individual projects.
5.  **Database (SQLAlchemy):** The final analysis result is stored in the database.
6.  **Response:** The complete analysis object is sent back to the frontend as a JSON response to be dynamically rendered.

-----

## ⚙️ Local Setup and Installation

Follow these steps to get the application running on your local machine.

#### **1. Prerequisites**

  * Python 3.10 or higher
  * Git

#### **2. Clone & Setup**

```bash
# Clone the repository
git clone https://github.com/nagmanijha/ResumeRev.ai
cd resume-parser

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate

# Install all required dependencies
pip install -r requirements.txt

# Download necessary NLP models
python -m spacy download en_core_web_sm
python -m textblob.download_corpora
```

#### **3. Environment Variables**

  * Create a file named **`.env`** in the root directory.
  * Add your Google Gemini API key to it:
    ```
    GEMINI_API_KEY=YOUR_API_KEY_HERE
    ```

#### **4. (Optional) Setup for RAG Suggestions**

To enable the advanced RAG-powered suggestions, you need to populate the local vector database.

  * Create a folder in the root directory named **`successful_resumes`**.
  * Place some high-quality example resumes (`.pdf` or `.docx`) inside it.
  * Run the one-time ingestion script:
    ```bash
    python ingest_examples.py
    ```

-----

## ▶️ Running the Application

1.  **Start the web server:**
    ```bash
    uvicorn main:app --reload
    ```
2.  **Open your browser** and navigate to `http://localhost:8000`.

-----

## 🗺️ Future Roadmap

This project is built on a scalable foundation. Future improvements include:

  * **Full User Authentication System:** Implement a complete login/registration system with JWT.
  * **Resume Version Control:** Allow users to save and compare different versions of their resumes.
  * **Collaborative Commenting:** Enable users or coaches to leave inline comments on resume sections.

-----

## 📜 License

This project is distributed under the MIT License. See `LICENSE` for more information.


