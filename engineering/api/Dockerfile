# Build stage — install dependencies using uv
FROM ghcr.io/astral-sh/uv:0.13.8-python3.13-alpine@sha256:f2d6278d0821c35881b010ddbf75825049661a98dbfdf61bbd1407e8dd544d00 AS build

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .
RUN uv sync --frozen --no-dev


# Dev
FROM ghcr.io/astral-sh/uv:0.13.8-python3.13-alpine@sha256:f2d6278d0821c35881b010ddbf75825049661a98dbfdf61bbd1407e8dd544d00 AS dev

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
FROM python:3.13.18-alpine@sha256:9ef1a599f863231c3d91e941389bfdc4a2d6070557243d54df1a4e57015b960e AS app

# The app runs from the venv; the base image's pip, with its vendored urllib3,
# msgpack, and setuptools, would only add unpatched packages to scans.
# Fixes the pinned base image predates: zlib 1.4 (CVE-2026-4738) and OpenSSL
# 3.5.9-r1 (CVE-2026-107496).
RUN apk upgrade --no-cache zlib libcrypto3 libssl3 && \
    python -m pip uninstall -y pip && \
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
