#!/bin/bash
# Turns each Bible version in BibleSources (English, Korean, Thai …) into an edition of the passages
# ChineseReaderText already has — one git branch per version, so they can be checked and merged one
# at a time:
#
#   version/en/kjv     bible/passages/romans-12.kjv.md, genesis-1.kjv.md …  + the Passages list
#   version/ko/krv     … romans-12.krv.md (개역한글 right under the Chinese)
#   version/th/thkjv   … romans-12.thkjv.md (Thai KJV, with its CC BY-NC-ND notice)
#
# English versions replace the English row of the Study edition (Chinese, Greek or Hebrew, then
# the version); Korean and Thai versions are added right after the Chinese, with the WEB under them.
# Only versions that may be published (public domain, Creative Commons) unless --include-restricted.
#
#   bible/version_branches.sh --list                 # what it would do
#   bible/version_branches.sh                        # every English, Korean and Thai version
#   bible/version_branches.sh --lang ko,th
#   bible/version_branches.sh --versions kjv,krv
#   bible/version_branches.sh --force                # rebuild branches that already exist
#
# Each branch is made from the branch you're on (main), committed, and left unpushed; you come
# back to where you started. ChineseReaderText must be clean first (commit or stash).
#   Look at one:  git -C ../ChineseReaderText diff main..version/en/kjv --stat
#   Take it:      git -C ../ChineseReaderText merge version/en/kjv
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
TOOLS="$(cd "$HERE/.." && pwd)"
TEXT="${TEXT_REPO:-$(cd "$TOOLS/../ChineseReaderText" && pwd)}"
LANGS="en,ko,th"
VERSIONS=""
RESTRICTED=""
FORCE=""
LIST=""

while [ $# -gt 0 ]; do
    case "$1" in
        --lang) LANGS="$2"; shift 2 ;;
        --versions) VERSIONS="$2"; shift 2 ;;
        --include-restricted) RESTRICTED="--include-restricted"; shift ;;
        --force) FORCE=1; shift ;;
        --list) LIST=1; shift ;;
        -h|--help) sed -n '2,25p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "unknown option: $1 (--help)"; exit 2 ;;
    esac
done

cd "$TOOLS"
# The Python with pypinyin and jieba: a .venv in ChineseReaderTools or ChineseReaderText, else python3.
# (Set PYTHON to choose another.)
PY="${PYTHON:-python3}"
if [ -z "${PYTHON:-}" ]; then
    for venv in "$TOOLS/.venv" "$TEXT/.venv"; do
        "$venv/bin/python3" -c "import pypinyin, jieba" 2>/dev/null && { PY="$venv/bin/python3"; break; }
    done
fi
PLAN="$($PY bible/version_plan.py --lang "$LANGS" --versions "$VERSIONS" --text-repo "$TEXT" $RESTRICTED)"

echo "ChineseReaderText: $TEXT"
echo "$PLAN" | awk -F'\t' '
    /^#skip/ { printf "  skip      %-14s %s\n", $2, $3; next }
    NF       { n = split($8, p, ";"); printf "  %-22s %-14s %-12s %d passages  (%s)\n", $5, $1, $6, n, $7 }'
[ -n "$LIST" ] && exit 0

git -C "$TEXT" rev-parse --verify -q HEAD >/dev/null || { echo "ChineseReaderText has no commits yet."; exit 1; }
if [ -n "$(git -C "$TEXT" status --porcelain)" ]; then
    echo "ChineseReaderText has changes that aren't committed — commit or stash them first:"
    git -C "$TEXT" status --short | head -10
    exit 1
fi
START="$(git -C "$TEXT" rev-parse --abbrev-ref HEAD)"
trap 'git -C "$TEXT" checkout -q "$START" 2>/dev/null || true' EXIT

made=0
while IFS=$'\t' read -r key edition lang option branch label license refs; do
    [ -z "$key" ] && continue
    case "$key" in \#*) continue ;; esac
    if git -C "$TEXT" rev-parse --verify -q "refs/heads/$branch" >/dev/null; then
        if [ -z "$FORCE" ]; then
            echo "  $branch exists — skipped (--force rebuilds it)"
            continue
        fi
        git -C "$TEXT" branch -q -D "$branch"
    fi
    echo "▸ $branch  ($label)"
    git -C "$TEXT" checkout -q -b "$branch" "$START"
    IFS=';' read -r -a passages <<< "$refs"
    if ! $PY bible/bible_pages.py "${passages[@]}" --as "$edition" "$option" "$key" \
            --text-repo "$TEXT" > /tmp/version_branches.log 2>&1; then
        echo "  ✗ building failed — see /tmp/version_branches.log; branch removed"
        cat /tmp/version_branches.log | tail -5
        git -C "$TEXT" checkout -q -f "$START"
        git -C "$TEXT" branch -q -D "$branch"
        continue
    fi
    git -C "$TEXT" add bible
    git -C "$TEXT" commit -q -m "Bible: $label ($key) as an edition of ${#passages[@]} passages" \
        -m "Version: $key — license: $license. Built by ChineseReaderTools bible/version_branches.sh."
    echo "  ✓ $(git -C "$TEXT" diff --stat "$START" HEAD | tail -1)"
    git -C "$TEXT" checkout -q "$START"
    made=$((made + 1))
done <<< "$PLAN"

echo
echo "$made branch(es) made from $START. Each: git -C \"$TEXT\" log --oneline $START..<branch>"
echo "To see one in the simulator: check it out, then set Settings › Developer › Local library folder."
