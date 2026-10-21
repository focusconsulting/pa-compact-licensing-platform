# Local tooling only: never built for or deployed to AWS.
FROM jagregory/cognito-local:latest@sha256:a5ad30d01da5016a38535a717f6e1642d1b37f886a7b17e90b67f6e5ad134831
COPY db /app/.cognito/db
HEALTHCHECK --interval=2s --timeout=2s --retries=15 CMD wget -qO- http://127.0.0.1:9229/local_licensing/.well-known/jwks.json || exit 1
