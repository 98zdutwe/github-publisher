#!/usr/bin/env python3
"""Build, commit and push in one step. Works in cmd, PowerShell and Git Bash.

Usage:
    python publish.py                     auto-generated commit message
    python publish.py "fix typo"          your own commit message
    python publish.py --no-build "..."    commit without rebuilding the feed

Exit codes:
    0  published, or nothing to publish
    1  something went wrong
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def say(text: str = "") -> None:
    print(text, flush=True)


def die(text: str) -> "None":
    print(f"error: {text}", file=sys.stderr, flush=True)
    raise SystemExit(1)


def run(cmd: list[str], quiet: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=quiet,
        check=False,
    )


def git(*args: str, quiet: bool = True) -> subprocess.CompletedProcess:
    return run(["git", *args], quiet=quiet)


def require_repo() -> None:
    if git("rev-parse", "--git-dir").returncode != 0:
        die(f"not a git repository: {ROOT}")

    if git("remote", "get-url", "origin").returncode != 0:
        die("no 'origin' remote. Run:\n"
            "  git remote add origin git@github.com:<user>/<repo>.git")

    if not (ROOT / "source" / "items.json").exists():
        die("source/items.json is missing.")


def build() -> None:
    script = ROOT / "scripts" / "build_feed.py"
    if not script.exists():
        die("scripts/build_feed.py is missing.")

    say("> rebuilding public/data")
    result = run([sys.executable, str(script)], quiet=False)
    if result.returncode != 0:
        die("build failed, nothing was committed.")


def commit(message: str) -> tuple[bool, str]:
    """Returns (committed, short_sha)."""
    git("add", "-A")

    # --quiet exits 0 when there is nothing staged, 1 when there is.
    if git("diff", "--cached", "--quiet").returncode == 0:
        say("no local changes.")
        return False, ""

    if not message:
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        message = f"update: {stamp}"

    result = git("commit", "-q", "-m", message)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        die(f"commit failed.\n{detail}")

    sha = git("rev-parse", "--short", "HEAD").stdout.strip()
    say(f"> committed {sha}  {message}")
    return True, sha


def push(branch: str, remote_exists: bool) -> None:
    if remote_exists:
        say("> pushing to origin")
        result = git("push", quiet=False)
        if result.returncode != 0:
            say("")
            say("push rejected. The remote has commits you do not have locally.")
            say("fix with:  git pull --rebase")
            say("then:      python publish.py")
            raise SystemExit(1)
        return

    say(f"> remote branch '{branch}' does not exist yet, pushing for the first time")
    result = git("push", "-u", "origin", "HEAD", quiet=False)
    if result.returncode != 0:
        say("")
        say("push failed. Check the remote and your SSH key:")
        say("  git remote -v")
        say("  ssh -T git@github.com")
        raise SystemExit(1)


def report() -> None:
    remote = git("remote", "get-url", "origin").stdout.strip()

    say("")
    if "github.com" in remote:
        slug = remote.split("github.com")[-1].lstrip(":/")
        if slug.endswith(".git"):
            slug = slug[:-4]
        owner, _, name = slug.partition("/")
        say("published.")
        say(f"  repo  https://github.com/{slug}")
        say(f"  page  https://{owner}.github.io/{name}/")
        say(f"  json  https://raw.githubusercontent.com/{slug}/main/public/data/latest.json")
        say(f"  cdn   https://cdn.jsdelivr.net/gh/{slug}@main/public/data/latest.json")
    else:
        say(f"published to {remote}")


def main() -> int:
    parser = argparse.ArgumentParser(
        add_help=True,
        description="Build, commit and push content in one step.",
    )
    parser.add_argument("message", nargs="?", default="", help="commit message")
    parser.add_argument("--no-build", action="store_true", help="skip rebuilding public/data")
    args = parser.parse_args()

    require_repo()

    branch = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip() or "main"

    # Without this, a repository that has commits but was never pushed would be
    # reported as "nothing to publish" and never reach GitHub.
    remote_exists = git("ls-remote", "--exit-code", "--heads", "origin", branch).returncode == 0

    if not args.no_build:
        build()

    committed, _ = commit(args.message)

    if not committed and remote_exists:
        say("nothing to publish - the remote already has everything.")
        return 0

    push(branch, remote_exists)
    report()
    return 0


if __name__ == "__main__":
    sys.exit(main())
