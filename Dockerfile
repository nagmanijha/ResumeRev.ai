# Use Python 3.11 to ensure compatibility with spacy/blis wheels
FROM python:3.11-slim

# Install system build dependencies (fixes "gcc failed" errors for source builds)
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    # Install CPU-only PyTorch first to avoid downloading 3GB+ CUDA wheels
    pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Expose the port Render expects (default 10000 or 8000)
EXPOSE 8000

# Command to run the application
# We use backend.main:app because the file is in backend/main.py
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
