# Local tooling only: never built for or deployed to AWS.
FROM wiremock/wiremock:3.13.2@sha256:0d4ecb3e4dc8213fd7a4d37d6a78f6e6b553a6d2e15bd51b0999781282ac61b3
COPY mappings /home/wiremock/mappings
HEALTHCHECK --interval=2s --timeout=2s --retries=15 CMD wget -qO- http://127.0.0.1:8080/__admin/health || exit 1
