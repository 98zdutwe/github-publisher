#!/usr/bin/env python3
"""Edit source/items.json without hand-writing JSON.

Hand-editing JSON is the easiest way to break the build: one missing comma and
everything stops. This tool does the editing for you.

Usage:
    python scripts/new_entry.py list
    python scripts/new_entry.py add    --title "..." [options]
    python scripts/new_entry.py update --id ID [options]
    python scripts/new_entry.py remove --id ID

Options for add / update:
    --title TEXT          required for add
    --summary TEXT        short description
    --url URL             link to the full item
    --tags a,b,c          comma separated
    --date YYYY-MM-DD     defaults to today
    --id ID               defaults to <date>-<slug of title>

Examples:
    python scripts/new_entry.py add --title "Weekly notes, week 45" \
        --summary "Three things worth sharing." --tags notes,weekly

    python scripts/new_entry.py update --id 2026-11-09-weekly-notes-week-45 \
        --summary "Revised summary."

    python scripts/new_entry.py remove --id 2026-11-02-setup

After editing, run ./publish.sh to build and push.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "source" / "items.json"


def slug(text: str, limit: int = 40) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:limit] or "entry"


def load() -> list[dict]:
    if not SOURCE.exists():
        raise SystemExit(f"Source file not found: {SOURCE}")
    try:
        data = json.loads(SOURCE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(
            f"{SOURCE} is not valid JSON: line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc
    if not isinstance(data, list):
        raise SystemExit("Top level of source/items.json must be a JSON array")
    return data


def save(items: list[dict]) -> None:
    items.sort(key=lambda x: (x.get("date", ""), x.get("id", "")), reverse=True)
    text = json.dumps(items, ensure_ascii=False, indent=2) + "\n"
    SOURCE.write_text(text, encoding="utf-8", newline="\n")


def find(items: list[dict], entry_id: str) -> dict:
    for item in items:
        if item.get("id") == entry_id:
            return item
    raise SystemExit(f"No entry with id '{entry_id}'. Run 'list' to see existing ids.")


def cmd_list(args: argparse.Namespace) -> int:
    items = load()
    if not items:
        print("(no entries)")
        return 0
    items = sorted(items, key=lambda x: (x.get("date", ""), x.get("id", "")), reverse=True)
    for item in items:
        print(f"{item.get('date', '?'):12} {item.get('id', '?'):45} {item.get('title', '')}")
    print(f"\n{len(items)} entr{'y' if len(items) == 1 else 'ies'}")
    return 0


def cmd_add(args: argparse.Namespace) -> int:
    items = load()
    when = args.date or date.today().isoformat()
    entry_id = args.id or f"{when}-{slug(args.title)}"

    if any(i.get("id") == entry_id for i in items):
        raise SystemExit(f"Entry '{entry_id}' already exists. Use update instead.")

    entry = {
        "id": entry_id,
        "date": when,
        "title": args.title,
        "summary": args.summary or "",
        "url": args.url or "",
        "tags": [t.strip() for t in (args.tags or "").split(",") if t.strip()],
    }
    items.append(entry)
    save(items)
    print(f"added: {entry_id}")
    return 0


def cmd_update(args: argparse.Namespace) -> int:
    items = load()
    entry = find(items, args.id)

    if args.title is not None:
        entry["title"] = args.title
    if args.summary is not None:
        entry["summary"] = args.summary
    if args.url is not None:
        entry["url"] = args.url
    if args.date is not None:
        entry["date"] = args.date
    if args.tags is not None:
        entry["tags"] = [t.strip() for t in args.tags.split(",") if t.strip()]

    save(items)
    print(f"updated: {args.id}")
    return 0


def cmd_remove(args: argparse.Namespace) -> int:
    items = load()
    entry = find(items, args.id)
    items.remove(entry)
    save(items)
    print(f"removed: {args.id}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Edit source/items.json safely.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="show all entries")
    p_list.set_defaults(func=cmd_list)

    p_add = sub.add_parser("add", help="add a new entry")
    p_add.add_argument("--title", required=True)
    p_add.add_argument("--summary")
    p_add.add_argument("--url")
    p_add.add_argument("--tags")
    p_add.add_argument("--date")
    p_add.add_argument("--id")
    p_add.set_defaults(func=cmd_add)

    p_upd = sub.add_parser("update", help="change fields of an existing entry")
    p_upd.add_argument("--id", required=True)
    p_upd.add_argument("--title")
    p_upd.add_argument("--summary")
    p_upd.add_argument("--url")
    p_upd.add_argument("--tags")
    p_upd.add_argument("--date")
    p_upd.set_defaults(func=cmd_update)

    p_rm = sub.add_parser("remove", help="delete an entry")
    p_rm.add_argument("--id", required=True)
    p_rm.set_defaults(func=cmd_remove)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
