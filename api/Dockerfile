# Build stage — install dependencies using uv
FROM ghcr.io/astral-sh/uv:python3.13-alpine AS build

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .
RUN uv sync --frozen --no-dev


# Dev
FROM ghcr.io/astral-sh/uv:python3.13-alpine AS dev

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY . .

RUN adduser -u 5678 -D appuser && chown -R appuser /app
USER appuser

RUN uv sync --frozen

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "licensing_api.__main__:app", "--reload", "--host=0.0.0.0"]


# Prod
FROM python:3.13-alpine AS app

RUN addgroup -g 1000 python && \
    adduser -u 1000 -G python -D python

RUN mkdir /app && chown python:python /app
WORKDIR /app

COPY --chown=python:python --from=build /app/.venv /app/.venv
COPY --chown=python:python . .

USER 1000

ENV PATH="/app/.venv/bin:$PATH"
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "licensing_api.__main__:app"]
