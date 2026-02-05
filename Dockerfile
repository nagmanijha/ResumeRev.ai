# Use full Python 3.11 image to include all standard libraries and build tools
FROM python:3.11

WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
# 1. Upgrade build tools
# 2. Pin numpy<2.0 to avoid compatibility issues with older libs (blis/spacy)
# 3. Install CPU-only PyTorch
# 4. Install remaining requirements
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir "numpy<2.0" && \
    pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Expose the port Render expects (default 10000 or 8000)
EXPOSE 8000

# Command to run the application
# We use backend.main:app because the file is in backend/main.py
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
