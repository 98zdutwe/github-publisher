# github-publisher

A minimal setup for publishing content on GitHub that is readable by both
people (a web page) and programs (plain JSON over HTTPS).

Edit one file, run one command, and the content is live.

## Layout

```
source/items.json              the only file you normally edit
scripts/build_feed.py          turns the source file into public JSON
scripts/new_entry.py           helper for editing items.json safely
publish.sh                     build + commit + push in one step
public/                        everything GitHub Pages serves
  index.html                   the page people read
  .nojekyll                    serve files as-is, no Jekyll processing
  data/latest.json             20 newest records + metadata
  data/all.json                every record
  data/meta.json               metadata only
.github/workflows/publish.yml  scheduled build and deploy
```

## Everyday use

```bash
# 1. change something
python scripts/new_entry.py add --title "Release 1.2" --summary "What changed." --tags release

# or edit any file directly with your own editor

# 2. publish
./publish.sh "add release 1.2"
```

`publish.sh` rebuilds the feed, commits everything, pushes, and prints the
public URLs. It stops with a clear message if there is nothing to commit or if
the push is rejected.

### Editing entries

```bash
python scripts/new_entry.py list
python scripts/new_entry.py add    --title "..." [--summary ...] [--url ...] [--tags a,b] [--date YYYY-MM-DD]
python scripts/new_entry.py update --id ID [--title ...] [--summary ...]
python scripts/new_entry.py remove --id ID
```

Use the helper rather than editing `items.json` by hand: a single missing comma
makes the JSON invalid and the build fails. If you do edit it by hand,
`./publish.sh` will report the exact line and column of any syntax error.

### If you only changed a page

`./publish.sh` works for any file. For example, edit `public/index.html`, run
`./publish.sh "restyle header"`. Use `./publish.sh --no-build "..."` when you
want to skip regenerating `public/data`.

## First-time setup on a new machine

```bash
git clone git@github.com:98zdutwe/github-publisher.git
cd github-publisher
chmod +x publish.sh
```

Requires `git` and `python3` (or `python`). No packages to install.

## Public endpoints

Replace `OWNER` and `REPO` with your own:

| Purpose | URL |
|---|---|
| Web page | `https://OWNER.github.io/REPO/` |
| Raw file | `https://raw.githubusercontent.com/OWNER/REPO/main/public/data/latest.json` |
| CDN (faster, long cache) | `https://cdn.jsdelivr.net/gh/OWNER/REPO@main/public/data/latest.json` |
| Directory listing | `https://api.github.com/repos/OWNER/REPO/contents/public/data` |

Both `raw.githubusercontent.com` and jsDelivr send `Access-Control-Allow-Origin: *`,
so browser `fetch()` works cross-origin without a proxy.

Caching behaviour:

- `raw.githubusercontent.com` caches for roughly 5 minutes.
- jsDelivr caches `@main` for about 12 hours. Pin a commit SHA or a tag
  (`@v1.0.0`) when you need an immutable URL.
- The GitHub REST API allows 60 unauthenticated requests per hour. Fine for
  occasional directory listings, too low for polling.

## Schedule

`.github/workflows/publish.yml` runs on every push to `main` and daily at
01:00 UTC (09:00 Beijing time). Change the cron expression to adjust; it is
always in UTC.

```yaml
- cron: "0 1 * * *"     # daily at 01:00 UTC
- cron: "0 * * * *"     # hourly
- cron: "0 1 * * 1"     # Mondays at 01:00 UTC
```

Two things worth knowing: scheduled runs can be delayed by several minutes, and
GitHub pauses schedules on public repositories after 60 days without commit
activity. Any push re-enables it.

## License

- Code (`scripts/`, `.github/`, `public/index.html`, `publish.sh`) is MIT, see [LICENSE](LICENSE).
- Content data (`source/`, `public/data/`) is CC BY 4.0. Attribution required.

## Notes

- Everything in a public repository is readable by anyone, anonymously. Never
  commit secrets, tokens, or private data. Use GitHub Secrets or environment
  variables instead.
- Keep large binaries out of git. Past a few tens of megabytes, use release
  assets or object storage and commit only an index.
