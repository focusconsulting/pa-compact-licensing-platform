#!/usr/bin/env bash
# Builds the static site, serves it, and runs pa11y-ci (axe, WCAG 2 AA) over the
# pages in .pa11yci.json. Unlike the axe checks in the unit tests, this runs in a
# real browser, so it also catches colour contrast.
set -euo pipefail
cd "$(dirname "$0")/.."

pnpm build
pnpm exec serve out -l 3100 >/dev/null 2>&1 &
server=$!
trap 'kill "$server"' EXIT

for _ in $(seq 30); do
  curl -sf http://localhost:3100/ >/dev/null && break
  sleep 1
done
pnpm exec pa11y-ci --config .pa11yci.json
