#!/usr/bin/env python3
"""Turn source/items.json into the public data files.

Input:
    source/items.json     A JSON array. Each element is one record you maintain.

Output:
    public/data/latest.json   Most recent 20 records plus metadata.
    public/data/all.json      Every record.
    public/data/meta.json     Metadata only, smallest possible payload.

Standard library only. No dependencies to install.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "source" / "items.json"
OUT_DIR = ROOT / "public" / "data"
LATEST_LIMIT = 20

REQUIRED = ("id", "date", "title")


def load_items() -> list[dict]:
    if not SOURCE.exists():
        raise SystemExit(f"Source file not found: {SOURCE}")

    with SOURCE.open("r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as exc:
            raise SystemExit(
                f"{SOURCE} is not valid JSON: line {exc.lineno}, column {exc.colno}: {exc.msg}"
            ) from exc

    if not isinstance(data, list):
        raise SystemExit("Top level of source/items.json must be a JSON array")

    seen: set[str] = set()
    cleaned: list[dict] = []

    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise SystemExit(f"Entry #{i} is not an object")

        missing = [k for k in REQUIRED if not item.get(k)]
        if missing:
            raise SystemExit(f"Entry #{i} is missing required field(s): {', '.join(missing)}")

        if item["id"] in seen:
            raise SystemExit(f"Duplicate id: {item['id']}")
        seen.add(item["id"])

        record = dict(item)
        record.setdefault("summary", "")
        record.setdefault("url", "")
        record.setdefault("tags", [])
        cleaned.append(record)

    cleaned.sort(key=lambda x: (x["date"], x["id"]), reverse=True)
    return cleaned


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")


def main() -> int:
    items = load_items()
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    meta = {
        "generated_at": now,
        "total": len(items),
        "latest_date": items[0]["date"] if items else None,
        "schema_version": 1,
    }

    write_json(OUT_DIR / "meta.json", meta)
    write_json(OUT_DIR / "latest.json", {**meta, "items": items[:LATEST_LIMIT]})
    write_json(OUT_DIR / "all.json", {**meta, "items": items})

    print(f"Built {len(items)} record(s) at {now}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
