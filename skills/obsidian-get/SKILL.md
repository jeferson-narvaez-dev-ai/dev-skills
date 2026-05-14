---
name: obsidian-get
description: >
  Reads a note from an Obsidian vault, parsing frontmatter and body separately. Falls back to fuzzy title search if the exact path is not found.
  Trigger: When the user wants to read, view, open, or retrieve a note from Obsidian. Examples: "get obsidian note", "read vault note", "show me my note about X", "/obsidian-get".
license: MIT
metadata:
  author: jeferson narvaez
  version: "2.0"
---

## Purpose

Read a Markdown note from an Obsidian vault. Parses and displays YAML frontmatter and body content separately. Resolves the note path automatically using the taxonomy from `obsidian-save` v2.0 when a full path is not provided. Falls back to fuzzy title search if not found.

---

## Note Type Taxonomy

| Type | Path pattern |
|------|-------------|
| `exploration` | `{project}/{branch}/exploration/{name}-{date}.md` |
| `plan` | `{project}/{branch}/plan/{name}-{date}.md` |
| `issue` | `{project}/{branch}/issue/{name}-{date}.md` |
| `implementation` | `{project}/{branch}/implementation/{name}-{date}.md` |
| `review` | `{project}/{branch}/review/{name}-{date}.md` |

---

## Vault Resolution

Load `obsidian-file-system` skill first — it is the single source of truth for all paths and defines `$VAULT` and `$PROJECTS`.

- `$VAULT` — absolute path to the Obsidian vault (documentation only)
- `$PROJECTS` — absolute path to source code repositories

All note paths follow: `$VAULT/{project}/{branch-folder}/{type}/{name}-{date}.md`
Consult `obsidian-file-system` for vault structure, branch naming, and path construction.

---

## Inputs

| Input | Required | Description |
|-------|----------|-------------|
| `note_path` | No | Full relative path from vault root. If provided, skips auto-resolution. |
| `note_name` | No | Short note name (without date/path). Used with `note_type` to auto-resolve. |
| `note_type` | No | One of: `exploration`, `plan`, `execution`, `incident`. |

At least one of `note_path` or `note_name` is required.

---

## Steps

### 1. Resolve vault path

Use the vault resolution logic above.

### 2. Resolve note path

**If `note_path` is provided:** use it directly (append `.md` if missing).

**If not provided:** resolve using taxonomy:

```bash
PROJECT=$(basename "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null || echo "general")
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")
DATE=$(date +%Y-%m-%d)
```

Ask for `note_type` if not provided, then build path:

```bash
case "{note_type}" in
  exploration)    NOTE="$VAULT/$PROJECT/$BRANCH/exploration/{note_name}-$DATE.md" ;;
  plan)           NOTE="$VAULT/$PROJECT/$BRANCH/plan/{note_name}-$DATE.md" ;;
  issue)          NOTE="$VAULT/$PROJECT/$BRANCH/issue/{note_name}-$DATE.md" ;;
  implementation) NOTE="$VAULT/$PROJECT/$BRANCH/implementation/{note_name}-$DATE.md" ;;
  review)         NOTE="$VAULT/$PROJECT/$BRANCH/review/{note_name}-$DATE.md" ;;
esac
```

### 3. Check if file exists — fuzzy fallback

If the file does not exist, perform a fuzzy search by `note_name` across all `.md` files under `$VAULT/$PROJECT/` and show top 3 matches:

```bash
if [ ! -f "$NOTE" ]; then
  echo "Note not found: $NOTE"
  echo "Searching for similar notes..."
  find "$VAULT/$PROJECT" -name "*.md" -not -path "*/.obsidian/*" \
    | grep -i "{note_name}" \
    | head -3 \
    | while IFS= read -r match; do
        echo "  - ${match#$VAULT/}"
      done
  echo "Please re-run with a corrected path or name."
  exit 1
fi
```

### 4. Read and parse the note

```bash
python3 - <<'PYEOF'
note_path = "{resolved NOTE path}"

with open(note_path, "r", encoding="utf-8") as f:
    raw = f.read()

frontmatter = ""
body = raw

if raw.startswith("---"):
    parts = raw.split("---", 2)
    if len(parts) >= 3:
        frontmatter = parts[1].strip()
        body = parts[2].strip()

print("=== FRONTMATTER ===")
print(frontmatter if frontmatter else "(none)")
print("\n=== BODY ===")
print(body)
PYEOF
```

### 5. Display

Present output with clearly labeled sections:

```
=== FRONTMATTER ===
title: Plan AI15190 TID
type: plan
date: 2026-03-30

=== BODY ===
# Plan Minimalista...
```

---

## Rules

1. Always resolve vault before any file operation.
2. Always auto-append `.md` if the extension is missing.
3. If `note_path` not provided, use taxonomy + `note_name` + `note_type` to resolve.
4. If exact file not found, perform fuzzy search before giving up — show top 3 candidates.
5. Never use `import yaml` — split frontmatter with plain Python3 string splitting on `---`.
6. Always double-quote bash variable expansions to handle paths with spaces.
7. Display frontmatter and body in clearly labeled sections.