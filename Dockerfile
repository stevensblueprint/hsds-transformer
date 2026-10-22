FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN useradd --create-home nonroot

COPY --from=ghcr.io/astral-sh/uv:0.11.21 /uv /uvx /bin/
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-default-groups --extra api --no-install-project

COPY --chown=nonroot:nonroot . .

USER nonroot

ENV APP_MODULE=src.api.app:app \
    PORT=8000
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://localhost:{os.environ.get(\"PORT\", \"8000\")}/health', timeout=2)" || exit 1

CMD ["sh", "-c", "python -m uvicorn ${APP_MODULE} --host 0.0.0.0 --port ${PORT} --app-dir src"]
