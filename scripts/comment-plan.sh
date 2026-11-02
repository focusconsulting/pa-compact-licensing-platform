#!/usr/bin/env bash
# Post an OpenTofu plan on a pull request as one comment per component, replacing
# the previous one for that component. Used by .github/workflows/iac.yml.
#
#   comment-plan.sh <pr-number> <component> <plan.txt>
#
# Needs GH_TOKEN with pull-requests: write, and the repository in GH_REPO or git.
set -euo pipefail

pr="$1"
component="$2"
plan_file="$3"
marker="<!-- tofu-plan:${component} -->"
limit=60000 # GitHub caps a comment body at 65536 characters

summary=$(grep -E '^(Plan: |No changes\.|Error:)' "$plan_file" | head -1 || true)
: "${summary:=Plan did not finish; see the job log}"

plan=$(sed 's/\x1b\[[0-9;]*m//g' "$plan_file")
if [ "${#plan}" -gt "$limit" ]; then
  plan="${plan:0:$limit}

… truncated; the full plan is in the job log: ${GITHUB_SERVER_URL:-}/${GITHUB_REPOSITORY:-}/actions/runs/${GITHUB_RUN_ID:-}"
fi

body=$(printf '%s\n### `%s`: %s\n\n<details>\n<summary>Plan</summary>\n\n```\n%s\n```\n\n</details>\n' \
  "$marker" "$component" "$summary" "$plan")

existing=$(gh api "repos/{owner}/{repo}/issues/${pr}/comments" --paginate \
  --jq ".[] | select(.body | startswith(\"${marker}\")) | .id" | head -1)

if [ -n "$existing" ]; then
  gh api -X PATCH "repos/{owner}/{repo}/issues/comments/${existing}" -f body="$body" --silent
else
  gh api -X POST "repos/{owner}/{repo}/issues/${pr}/comments" -f body="$body" --silent
fi
