# Build stage — install dependencies using uv
FROM ghcr.io/astral-sh/uv:0.13.7-python3.13-alpine@sha256:7b02bf9f2d812bf1b21b4d790901eb22250523943b82af93e8c543ea54b6b4d5 AS build

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .
RUN uv sync --frozen --no-dev


# Dev
FROM ghcr.io/astral-sh/uv:0.13.7-python3.13-alpine@sha256:7b02bf9f2d812bf1b21b4d790901eb22250523943b82af93e8c543ea54b6b4d5 AS dev

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
FROM python:3.13.18-alpine@sha256:1e1f6334529d1fb26a2ef619d7cffb30a7c7d7cc1cc7338ebee283a58d1aeaca AS app

# The app runs from the venv; the base image's pip, with its vendored urllib3,
# msgpack, and setuptools, would only add unpatched packages to scans.
RUN python -m pip uninstall -y pip && \
    addgroup -g 1000 python && \
    adduser -u 1000 -G python -D python

RUN mkdir /app && chown python:python /app
WORKDIR /app

COPY --chown=python:python --from=build /app/.venv /app/.venv
COPY --chown=python:python . .

USER 1000

ENV PATH="/app/.venv/bin:$PATH"
# gunicorn behind TLS, with a certificate made at start (ADR-0019)
CMD ["python", "-m", "licensing_api.serve"]
