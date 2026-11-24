#!/usr/bin/env bash
# Build one delivery branch for the client repo: one area's paths, as they are at a
# commit of this repo, in a single commit on top of a base. The base is the client's
# main, or the branch of the area below it in a stack. Pushes nothing.
#
#   deliver.sh <source-repo> <commit> <delivery-clone> <base> <branch> <title> <area>
#
# <delivery-clone> is a clone of the client repo. <area> is a file name in areas/,
# without .txt.
set -euo pipefail

src=$1 commit=$(git -C "$1" rev-parse --verify "$2^{commit}") dst=$3 base=$4 branch=$5 title=$6 area=$7
here=$(cd "$(dirname "$0")" && pwd)
list() { grep -hvE '^\s*(#|$)' "$@"; }

# Export an area's paths at a commit, minus the excluded ones, into a new directory.
export_tree() { # <commit> <area> ; prints the directory
    local out paths=()
    out=$(mktemp -d)
    while read -r p; do
        if git -C "$src" cat-file -e "$1:$p" 2>/dev/null; then paths+=("$p"); fi
    done < <(list "$here/areas/$2.txt")
    git -C "$src" archive "$1" -- "${paths[@]}" | tar -x -C "$out"
    while read -r p; do
        case $p in
            */*) rm -rf "${out:?}/$p" ;;
            *) find "$out" -name "$p" -prune -exec rm -rf {} + ;;
        esac
    done < <(list "$here/exclude.txt")
    echo "$out"
}

git -C "$dst" checkout -q -B "$branch" "$base"

# Drift: for each area already on the base, the client's copy must still be what its
# latest delivery put there. A fix made in the client repo would otherwise be lost.
seen=" "
while IFS='|' read -r from delivered; do
    [ -n "$from" ] || continue
    case $seen in *" $delivered "*) continue ;; esac
    seen="$seen$delivered "
    expected=$(export_tree "$from" "$delivered")
    while read -r p; do
        [ -e "$expected/$p" ] || [ -e "$dst/$p" ] || continue
        diff -rq "$expected/$p" "$dst/$p" >/dev/null || { echo "drift: $p differs from delivery $from" >&2; exit 1; }
    done < <(list "$here/areas/$delivered.txt")
    rm -rf "$expected"
done < <(git -C "$dst" log "$base" --format='%(trailers:key=Source-Commit,valueonly,separator=)|%(trailers:key=Delivered-Area,valueonly,separator=)')

# Replace the area's paths, and only those, with the commit's.
new=$(export_tree "$commit" "$area")
while read -r p; do git -C "$dst" rm -rq --ignore-unmatch -- "$p"; rm -rf "${dst:?}/$p"; done < <(list "$here/areas/$area.txt")
cp -a "$new/." "$dst/"
rm -rf "$new"
git -C "$dst" add -A

git -C "$dst" commit -q -m "$title" -m "Source-Commit: $commit
Delivered-Area: $area"
git -C "$dst" show --stat --format='%h %s' HEAD | tail -1
