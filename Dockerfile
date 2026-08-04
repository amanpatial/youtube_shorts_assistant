FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Parent-style layout so `youtube_shorts_assistant` is importable as a package.
COPY requirements.txt /app/youtube_shorts_assistant/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/youtube_shorts_assistant/requirements.txt

COPY . /app/youtube_shorts_assistant/

WORKDIR /app
ENV PYTHONPATH=/app

RUN mkdir -p /app/youtube_shorts_assistant/data

EXPOSE 8000

# Default: ADK web UI for interactive use. Override CMD for CLI runs.
CMD ["adk", "web", "--host", "0.0.0.0", "--port", "8000", "/app"]
