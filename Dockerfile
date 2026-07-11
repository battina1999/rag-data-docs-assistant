FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=7860

RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && useradd -m -u 1000 user \
    && rm -rf /var/lib/apt/lists/*

USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH
WORKDIR $HOME/app

COPY --chown=user:user requirements.txt .
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

COPY --chown=user:user . .

EXPOSE 7860

# Build the index on start (uses OpenAI if OPENAI_API_KEY is set, else the
# free local provider), then serve on the Hugging Face Docker port.
CMD ["bash", "-lc", "python -m app.ingest && exec uvicorn app.api:app --host 0.0.0.0 --port ${PORT}"]
