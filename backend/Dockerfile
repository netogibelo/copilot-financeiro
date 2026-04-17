FROM python:3.11-slim

WORKDIR /app

# System dependencies for OCR and ML
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-por \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Download NLTK data
RUN python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
