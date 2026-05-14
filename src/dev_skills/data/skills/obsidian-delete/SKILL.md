---
name: obsidian-delete
description: >
  Deletes a note from an Obsidian vault after showing a preview and requiring explicit user confirmation.
  Trigger: When the user wants to delete, remove, or erase a note from Obsidian. Examples: "delete obsidian note", "remove note from vault", "erase my note", "/obsidian-delete".
license: MIT
metadata:
  author: jeferson narvaez
  version: "2.0"
---

## Purpose

Safely delete a Markdown note from an Obsidian vault. Always shows the user a preview of the note before asking for explicit confirmation. Uses the same path taxonomy as `obsidian-save` v2.0 to resolve the note path when not provided. Never deletes without a clear "YES" from the user.

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
| `note_name` | No | Short note name. Used with `note_type` to auto-resolve path. |
| `note_type` | No | One of: `exploration`, `plan`, `issue`, `implementation`, `review`. |

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

If the resolved path does not exist, perform a fuzzy search by `note_name` under `$VAULT/$PROJECT/` and show top 3 candidates before aborting.

### 3. Verify file exists

```bash
if [ ! -f "$NOTE" ]; then
  echo "Note not found: $NOTE"
  exit 1
fi
```

### 4. Show preview (first 5 lines) — REQUIRED before confirmation

```bash
echo "=== Note to delete ==="
echo "Path: $NOTE"
echo ""
echo "--- Preview (first 5 lines) ---"
head -5 "$NOTE"
echo "---"
```

### 5. Request explicit confirmation — REQUIRED

Claude MUST ask the user and wait for their response before proceeding:

```
Are you sure you want to permanently delete this note?
Type YES (all caps) to confirm, or anything else to cancel.
```

- If the user responds with exactly `YES` (case-sensitive): proceed to deletion.
- If anything else (`yes`, `y`, `no`, `cancel`, etc.): abort and inform the user the note was NOT deleted.

**Safety rule: Never delete the file without receiving an explicit "YES". Zero exceptions.**

### 6. Delete the note

Only execute after receiving "YES":

```bash
rm "$NOTE"
```

### 7. Confirm deletion

```bash
if [ ! -f "$NOTE" ]; then
  echo "Note deleted: $NOTE"
else
  echo "ERROR: Deletion failed for: $NOTE"
fi
```

---

## Rules

1. Always resolve vault before any file operation.
2. Always auto-append `.md` if the extension is missing.
3. If `note_path` not provided, use taxonomy + `note_name` + `note_type` to resolve.
4. If exact file not found, fuzzy search before giving up — show top 3 candidates.
5. **ALWAYS show the preview before asking for confirmation.**
6. **NEVER delete without an explicit "YES" (case-sensitive) from the user.**
7. `yes`, `y`, `confirm` or any other variant is NOT sufficient — only `YES` triggers deletion.
8. Always double-quote bash variable expansions to handle paths with spaces.
9. Confirm deletion succeeded by checking the file no longer exists.