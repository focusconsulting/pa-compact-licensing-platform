#!/usr/bin/env bash
# Build one delivery branch for the client repo: the paths of the named areas, as they
# are at a commit of this repo, in a single commit on top of the client's main. A
# delivery is cumulative: name every area delivered so far plus the new one. Pushes nothing.
#
#   deliver.sh <source-repo> <commit> <delivery-clone> <branch> <title> <area>...
#
# <delivery-clone> is a clone of the fork with the client repo as the remote `upstream`.
# <area> is a file name in areas/, without .txt.
set -euo pipefail

src=$1 commit=$(git -C "$1" rev-parse --verify "$2^{commit}") dst=$3 branch=$4 title=$5
shift 5
here=$(cd "$(dirname "$0")" && pwd)
list() { grep -hvE '^\s*(#|$)' "$@"; }
paths_of() { for a in "$@"; do list "$here/areas/$a.txt"; done; }

# Export the areas' paths at a commit, minus the excluded ones, into a new directory.
export_tree() { # <commit> <area>... ; prints the directory
    local c=$1 out paths=(); shift
    out=$(mktemp -d)
    while read -r p; do
        if git -C "$src" cat-file -e "$c:$p" 2>/dev/null; then paths+=("$p"); fi
    done < <(paths_of "$@")
    git -C "$src" archive "$c" -- "${paths[@]}" | tar -x -C "$out"
    while read -r p; do
        case $p in
            */*) rm -rf "${out:?}/$p" ;;
            *) find "$out" -name "$p" -prune -exec rm -rf {} + ;;
        esac
    done < <(list "$here/exclude.txt")
    echo "$out"
}

git -C "$dst" fetch -q upstream main
git -C "$dst" checkout -q -B "$branch" upstream/main

# Drift: the client's copy of what we delivered must still be what the last delivery put there.
trailer() { git -C "$dst" log upstream/main --format="%(trailers:key=$1,valueonly)" | grep -m1 . || true; }
last=$(trailer Source-Commit)
if [ -n "$last" ]; then
    read -ra last_areas <<<"$(trailer Delivered-Areas)"
    expected=$(export_tree "$last" "${last_areas[@]}")
    while read -r p; do
        [ -e "$expected/$p" ] || [ -e "$dst/$p" ] || continue
        diff -rq "$expected/$p" "$dst/$p" >/dev/null || { echo "drift: $p differs from delivery $last" >&2; exit 1; }
    done < <(paths_of "${last_areas[@]}")
    rm -rf "$expected"
fi

# Replace the areas' paths, and only those, with the commit's.
new=$(export_tree "$commit" "$@")
while read -r p; do git -C "$dst" rm -rq --ignore-unmatch -- "$p"; rm -rf "${dst:?}/$p"; done < <(paths_of "$@")
cp -a "$new/." "$dst/"
rm -rf "$new"
git -C "$dst" add -A

git -C "$dst" commit -q -m "$title" -m "Source-Commit: $commit
Delivered-Areas: $*"
git -C "$dst" show --stat --format='%h %s' HEAD | tail -1
