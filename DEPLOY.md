# Deployment Guide for ResumeRev.ai

This guide will help you deploy your full-stack ResumeRev.ai application to **Render**, a cloud platform that is easy to use and free for hobby projects.

## 1. Prerequisites
- A [GitHub](https://github.com) account.
- A [Render](https://render.com) account (you can sign up with GitHub).
- The project code pushed to a GitHub repository.

## 2. Prepare Your Project
Ensure your project structure looks like this (which it should currently):

```
resume_parser/
├── backend/
│   ├── main.py
│   ├── ...
├── frontend/
│   ├── index.html
│   ├── script.js
│   ├── styles.css
├── fonts/
│   ├── DejaVuSans.ttf
│   ├── ...
├── requirements.txt  <-- Created automatically
├── resume_analysis.db (Optional, will be recreated on server)
└── ...
```

## 3. Deployment Steps on Render

1.  **Push Code to GitHub**:
    - Initialize a git repo if you haven't: `git init`
    - Add files: `git add .`
    - Commit: `git commit -m "Ready for deploy"`
    - Push to a new GitHub repository.

2.  **Create Service on Render**:
    - Go to your [Render Dashboard](https://dashboard.render.com).
    - Click **New +** -> **Web Service**.
    - Connect your GitHub repository.

3.  **Configure Service**:
    - **Name**: `resumerev-ai` (or any name)
    - **Region**: Closest to you (e.g., Singapore, Frankfurt, Oregon)
    - **Branch**: `main` (or `master`)
    - **Runtime**: **Python 3**
    - **Build Command**: `pip install -r requirements.txt`
    - **Start Command**: `python -m uvicorn backend.main:app --host 0.0.0.0 --port 10000`

4.  **Environment Variables**:
    - Scroll down to "Environment Variables" and click **Add Environment Variable**.
    - Add your API Key:
        - **Key**: `GEMINI_API_KEY`
        - **Value**: `your_actual_api_key_here`
    - (Optional) **Key**: `APP_API_KEY`, **Value**: `any_secret_password` (if you want to lock the app)

5.  **Deploy**:
    - Click **Create Web Service**.
    - Render will start building your app. It may take 2-3 minutes.
    - Watch the logs. Once it says "Application startup...", your app is live!

## 4. Important Notes
- **Database**: This app uses SQLite (`resume_analysis.db`). On Render's free tier, the file system is "ephemeral", meaning if the server restarts (which happens occasionally), **the database will reset**. For a persistent production app, you would need to connect a PostgreSQL database, but for a demo/portfolio, SQLite is fine.
- **Fonts**: Ensure the `fonts/` directory is included in your git commit so the PDF generator works correctly.

## 5. Verification
- Once deployed, open the URL provided by Render (e.g., `https://resumerev-ai.onrender.com`).
- You should see the exact same UI as your local version.
