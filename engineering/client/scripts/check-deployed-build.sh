#!/usr/bin/env bash
# Fails if the static export in out/ contains the development-only list of seeded
# users (ADR-0020). Run it after a build that leaves NEXT_PUBLIC_DEV_SIGN_IN_PASSWORD
# empty, as a deploy does: the list's module is then compiled out, and with it the
# one call only that module makes.
set -euo pipefail
cd "$(dirname "$0")/.."

if found=$(grep -rl "AWSCognitoIdentityProviderService.ListUsers" out); then
  echo "The build contains the development-only sign-in list:" >&2
  echo "$found" >&2
  exit 1
fi
echo "The build has no development-only sign-in list."
