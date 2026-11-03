#!/usr/bin/env bash
#
# publish.sh - build, commit and push your content in one step.
#
# Usage:
#   ./publish.sh                        auto-generated commit message
#   ./publish.sh "fix typo in intro"    your own commit message
#   ./publish.sh --no-build "..."       commit without rebuilding the feed
#
# Run it from anywhere; the script locates the project folder itself.
#
# Exit codes:
#   0  published, or nothing to publish
#   1  something went wrong (message explains what)

set -euo pipefail

cd "$(dirname "$0")"

BUILD=1
MESSAGE=""

usage() {
    sed -n '3,15p' "$0" | sed 's/^# \{0,1\}//'
}

for arg in "$@"; do
    case "$arg" in
        --no-build) BUILD=0 ;;
        -h|--help)  usage; exit 0 ;;
        *)          MESSAGE="$arg" ;;
    esac
done

say() { printf '%s\n' "$*"; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

report() {
    local remote slug owner name
    remote=$(git remote get-url origin)

    case "$remote" in
        *github.com[:/]*)
            slug=$(printf '%s' "$remote" | sed -E 's#^.*github\.com[:/]##; s#\.git$##')
            owner=${slug%%/*}
            name=${slug##*/}
            say ""
            say "published."
            say "  repo  https://github.com/$slug"
            say "  page  https://$owner.github.io/$name/"
            say "  json  https://raw.githubusercontent.com/$slug/main/public/data/latest.json"
            say "  cdn   https://cdn.jsdelivr.net/gh/$slug@main/public/data/latest.json"
            ;;
        *)
            say ""
            say "published to $remote"
            ;;
    esac
}

# ---------------------------------------------------------------- checks

git rev-parse --git-dir >/dev/null 2>&1 \
    || die "not a git repository. Expected to find .git next to this script."

git remote get-url origin >/dev/null 2>&1 \
    || die "no 'origin' remote. Run: git remote add origin git@github.com:<user>/<repo>.git"

[ -f source/items.json ] || die "source/items.json is missing."

BRANCH=$(git rev-parse --abbrev-ref HEAD)

# Does the branch already exist on the remote? Needed so that a fresh clone or
# a re-created repository still gets its first push even with no new commits.
REMOTE_EXISTS=1
git ls-remote --exit-code --heads origin "$BRANCH" >/dev/null 2>&1 || REMOTE_EXISTS=0

# ---------------------------------------------------------------- build

if [ "$BUILD" -eq 1 ]; then
    if command -v python3 >/dev/null 2>&1; then
        PY=python3
    elif command -v python >/dev/null 2>&1; then
        PY=python
    else
        die "python not found in PATH."
    fi

    say "> rebuilding public/data"
    "$PY" scripts/build_feed.py
fi

# ---------------------------------------------------------------- commit

git add -A

if git diff --cached --quiet; then
    say "no local changes."
    COMMITTED=0
else
    if [ -z "$MESSAGE" ]; then
        MESSAGE="update: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    fi
    git commit -q -m "$MESSAGE"
    say "> committed $(git rev-parse --short HEAD)  $MESSAGE"
    COMMITTED=1
fi

# ---------------------------------------------------------------- push

if [ "$COMMITTED" -eq 0 ] && [ "$REMOTE_EXISTS" -eq 1 ]; then
    say "nothing to publish - the remote already has everything."
    exit 0
fi

if [ "$REMOTE_EXISTS" -eq 0 ]; then
    say "> remote branch '$BRANCH' does not exist yet, pushing for the first time"
    git push -u origin HEAD || {
        say ""
        say "push failed. Check that the repository exists and that your SSH key works:"
        say "  ssh -T git@github.com"
        say "and that the remote is right:"
        say "  git remote -v"
        exit 1
    }
else
    say "> pushing to origin"
    git push || {
        say ""
        say "push rejected. The remote has commits you do not have locally."
        say "fix with:  git pull --rebase"
        say "then:      ./publish.sh"
        exit 1
    }
fi

report
