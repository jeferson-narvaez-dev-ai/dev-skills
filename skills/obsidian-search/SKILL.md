---
name: obsidian-search
description: >
  Searches an Obsidian vault by title and content, returning ranked results with previews. Supports title-only mode and configurable result count.
  Trigger: When the user wants to search, find, or look up notes in Obsidian. Examples: "search obsidian vault", "find notes about X", "look up my obsidian notes", "/obsidian-search".
license: MIT
metadata:
  author: jeferson narvaez
  version: "1.0"
---

## Search Methods

> **Recommended**: Use `vault-search.py` (same directory as this skill) for fast local search. It uses ripgrep when available and falls back to Python. Only use the Grep tool directly for one-off searches — `vault-search.py` handles ranking, deduplication, and frontmatter parsing automatically.

## Script Usage

`vault-search.py` supports four modes. Pass `$VAULT` (defined by `obsidian-file-system`) as the last argument.

### Mode 1 — Title search
```bash
python3 ~/.claude/skills/obsidian-search/vault-search.py --title "payment flow" "$VAULT"
```
Fuzzy/partial matches against filenames and the first `# Heading`. Results ranked by score (exact match > partial match).

### Mode 2 — Content search
```bash
python3 ~/.claude/skills/obsidian-search/vault-search.py --content "PENDING transaction" "$VAULT"
```
Uses `rg` (ripgrep) if available, falls back to pure Python. Returns file path, matching line, limited to first 20 matches.

### Mode 3 — Frontmatter search
```bash
python3 ~/.claude/skills/obsidian-search/vault-search.py --frontmatter "canvas" "$VAULT"
```
Parses YAML frontmatter from each `.md` file. Matches if key or value contains the query. Returns file path and matched field(s).

### Mode 4 — Combined (default, no flag)
```bash
python3 ~/.claude/skills/obsidian-search/vault-search.py "payment" "$VAULT"
```
Runs title + content search in parallel (`concurrent.futures`). Deduplicates results — title matches rank first, then content matches. Limits output to 15 results.

### Output format (all modes)
```
[1] usrv-payouts-transfer/feature-PAY-123/exploration/payment-flow-2026-04-15.md
    Title: Payment Flow Analysis
    Modified: 2026-04-15
    Match: "...PENDING transaction created..."

[2] ...
```

---

## Purpose

Search an Obsidian vault for notes matching a query, using a two-pass scoring algorithm implemented in Python3. Results are ranked by relevance score and include a preview of the first matching line.

## Vault Resolution

Load `obsidian-file-system` skill first — it is the single source of truth for all paths and defines `$VAULT` and `$PROJECTS`.

- `$VAULT` — absolute path to the Obsidian vault (documentation only)
- `$PROJECTS` — absolute path to source code repositories

All note paths follow: `$VAULT/{project}/{branch-folder}/{type}/{name}-{date}.md`
Consult `obsidian-file-system` for vault structure, branch naming, and path construction.

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `query` | Yes | — | Search term. Treated as a fixed string (not regex) by default. |
| `top_n` | No | `5` | Number of top results to return. |
| `title_only` | No | `false` | If `true`, skip content search and match only on filenames. |

## Steps

### 1. Resolve vault path

Use the vault resolution logic above to determine `$VAULT`.

### 2. Auto-detect ripgrep

Check whether `rg` is available and prefer it over `grep` for content search:

```bash
if command -v rg &>/dev/null; then
  USE_RG=true
else
  USE_RG=false
fi
```

### 3. Run the two-pass scoring algorithm (Python3)

Use a single Python3 inline script to collect candidates, score them, sort, and display results. **Do NOT use bash associative arrays** — macOS ships with bash 3.2 which does not support them.

```bash
python3 - <<PYEOF
import subprocess
import os
import sys

vault = "$VAULT"
query = "$QUERY"
top_n = {top_n}
title_only = {title_only_bool}
use_rg = $USE_RG

scores = {}   # relative_path -> score
previews = {} # relative_path -> first matching line preview

# --- Pass 1: Title match (score +10 per hit) ---
find_result = subprocess.run(
    ["find", vault, "-name", "*.md", "-not", "-path", "*/.obsidian/*"],
    capture_output=True, text=True
)
for line in find_result.stdout.splitlines():
    line = line.strip()
    if not line:
        continue
    basename = os.path.basename(line).lower()
    if query.lower() in basename:
        rel = os.path.relpath(line, vault)
        scores[rel] = scores.get(rel, 0) + 10

# --- Pass 2: Content match (skip if title_only) ---
if not title_only:
    if use_rg:
        grep_cmd = ["rg", "-ril", "--fixed-strings", query, vault, "--glob", "*.md",
                    "--glob", "!.obsidian"]
    else:
        grep_cmd = ["grep", "-ril", "-F", query, vault, "--include=*.md",
                    "--exclude-dir=.obsidian"]

    grep_result = subprocess.run(grep_cmd, capture_output=True, text=True)
    content_files = [l.strip() for l in grep_result.stdout.splitlines() if l.strip()]

    for fpath in content_files:
        rel = os.path.relpath(fpath, vault)
        # Count matching lines for bonus score (capped at 5)
        if use_rg:
            count_cmd = ["rg", "-i", "--fixed-strings", "-c", query, fpath]
        else:
            count_cmd = ["grep", "-ic", "-F", query, fpath]
        count_result = subprocess.run(count_cmd, capture_output=True, text=True)
        try:
            match_count = int(count_result.stdout.strip())
        except ValueError:
            match_count = 0
        bonus = min(match_count, 5)
        scores[rel] = scores.get(rel, 0) + 5 + bonus

        # Get first matching line as preview
        if use_rg:
            preview_cmd = ["rg", "-i", "--fixed-strings", "-m1", query, fpath]
        else:
            preview_cmd = ["grep", "-i", "-F", "-m1", query, fpath]
        preview_result = subprocess.run(preview_cmd, capture_output=True, text=True)
        preview_line = preview_result.stdout.strip()
        if rel not in previews and preview_line:
            previews[rel] = preview_line[:120]  # truncate long lines

# --- Sort and display top N ---
ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_n]

if not ranked:
    print(f"No results found for: {query}")
    sys.exit(0)

print(f"Search results for '{query}' (top {top_n}):\n")
for i, (rel, score) in enumerate(ranked, 1):
    preview = previews.get(rel, "")
    print(f"{i}. [{score} pts] {rel}")
    if preview:
        print(f"   > {preview}")
    print()
PYEOF
```

## Display Format

Results are shown in ranked order:

```
Search results for 'kubernetes' (top 5):

1. [15 pts] DevOps/kubernetes-notes.md
   > ## Kubernetes is an open-source container orchestration platform

2. [10 pts] Projects/k8s-migration.md
   > tags: [kubernetes, migration]

3. [5 pts] Archive/old-infra.md
   > We migrated from kubernetes 1.18 to 1.24
```

## Rules

1. Always resolve vault before any file operation.
2. Use Python3 for all scoring logic — do NOT use bash associative arrays (macOS bash 3.2 incompatibility).
3. Use `grep -iF` (fixed string, case-insensitive) by default to safely handle special characters in queries.
4. Auto-detect `rg` via `command -v rg` and prefer it if available.
5. Pass 1 (title match) always runs. Pass 2 (content match) is skipped when `title_only=true`.
6. Score formula: title match = +10; content file found = +5; each matching line (capped at 5) = +1.
7. Always double-quote bash variable expansions to handle paths with spaces.
8. Truncate long preview lines to 120 characters.
9. If no results are found, display a clear "no results" message.
