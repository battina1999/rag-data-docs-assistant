FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

# Hugging Face Spaces (Docker SDK) routes traffic to 7860; override with PORT.
ENV PORT=7860
EXPOSE 7860 8000

# Build the index on start (uses OpenAI if OPENAI_API_KEY is set, else the
# free local provider), then serve.
CMD ["bash", "-lc", "python -m app.ingest && uvicorn app.api:app --host 0.0.0.0 --port ${PORT}"]
