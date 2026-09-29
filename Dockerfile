FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN useradd -m nonroot && chown -R nonroot /app
USER nonroot

COPY . .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

ENV APP_MODULE=api.app:app \
    PORT=8000
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://localhost:{os.environ.get(\"PORT\", \"8000\")}/health', timeout=2)" || exit 1

CMD ["sh", "-c", "python -m uvicorn ${APP_MODULE} --host 0.0.0.0 --port ${PORT} --app-dir src"]
