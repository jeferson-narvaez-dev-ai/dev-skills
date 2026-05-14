---
name: obsidian-edit
description: >
  Modifies an existing Obsidian note by appending, prepending, or replacing content. Confirms the change by showing modified context.
  Trigger: When the user wants to edit, update, append to, prepend to, or replace content in an Obsidian note. Examples: "append to obsidian note", "add text to vault note", "replace section in note", "/obsidian-edit".
license: MIT
metadata:
  author: jeferson narvaez
  version: "2.0"
---

## Purpose

Modify an existing Markdown note in an Obsidian vault using one of three modes: append, prepend, or replace. Uses the same path taxonomy as `obsidian-save` v2.0 to resolve the note path automatically when not provided.

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
| `note_name` | No | Short note name (without date/path). Used with `note_type` to auto-resolve path. |
| `note_type` | No | One of: `exploration`, `plan`, `issue`, `implementation`, `review`. Used with `note_name` to auto-resolve path. |
| `mode` | Yes | One of: `append`, `prepend`, `replace`. |
| `content` | Yes | The new content to insert or use as replacement. |
| `replace_pattern` | Only for `replace` mode | The exact string to find and replace (first occurrence only). |

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

Ask for `note_type` if not provided:

```
What type is the note to edit?
  1. exploration
  2. plan
  3. issue
  4. implementation
  5. review
```

Then build:

```bash
case "{note_type}" in
  exploration)    NOTE="$VAULT/$PROJECT/$BRANCH/exploration/{note_name}-$DATE.md" ;;
  plan)           NOTE="$VAULT/$PROJECT/$BRANCH/plan/{note_name}-$DATE.md" ;;
  issue)          NOTE="$VAULT/$PROJECT/$BRANCH/issue/{note_name}-$DATE.md" ;;
  implementation) NOTE="$VAULT/$PROJECT/$BRANCH/implementation/{note_name}-$DATE.md" ;;
  review)         NOTE="$VAULT/$PROJECT/$BRANCH/review/{note_name}-$DATE.md" ;;
esac
```

If the resolved path does not exist, perform a fuzzy search by `note_name` under `$VAULT/$PROJECT/` and show top 3 candidates.

### 3. Verify file exists

```bash
if [ ! -f "$NOTE" ]; then
  echo "Note not found: $NOTE"
  exit 1
fi
```

### 4. Apply the edit

#### Append mode

```bash
printf '\n%s' "{content}" >> "$NOTE"
```

#### Prepend mode

```bash
python3 - <<'PYEOF'
note_path = "{resolved NOTE path}"
new_content = """{content}"""

with open(note_path, "r", encoding="utf-8") as f:
    raw = f.read()

if raw.startswith("---"):
    parts = raw.split("---", 2)
    if len(parts) >= 3:
        result = "---" + parts[1] + "---\n" + new_content + "\n" + parts[2].lstrip("\n")
    else:
        result = new_content + "\n" + raw
else:
    result = new_content + "\n" + raw

with open(note_path, "w", encoding="utf-8") as f:
    f.write(result)

print(f"Prepended to: {note_path}")
PYEOF
```

#### Replace mode

```bash
python3 - <<'PYEOF'
note_path = "{resolved NOTE path}"
pattern = """{replace_pattern}"""
replacement = """{content}"""

with open(note_path, "r", encoding="utf-8") as f:
    raw = f.read()

if pattern not in raw:
    print(f"Pattern not found in note: {pattern}")
    raise SystemExit(1)

updated = raw.replace(pattern, replacement, 1)

with open(note_path, "w", encoding="utf-8") as f:
    f.write(updated)

print(f"Replaced first occurrence in: {note_path}")
PYEOF
```

### 5. Confirm by showing modified context

- **Append**: Show last 5 lines.
- **Prepend**: Show first 8 lines.
- **Replace**: Show 2 lines before/after the replacement.

---

## Rules

1. Always resolve vault before any file operation.
2. Always auto-append `.md` if the extension is missing.
3. If `note_path` is not provided, use the taxonomy + `note_name` + `note_type` to resolve. Ask for missing inputs.
4. If the resolved path does not exist, fuzzy search before giving up.
5. If the file does not exist, abort — do not create a new file.
6. `replace` mode only replaces the first occurrence.
7. Never use `import yaml`.
8. Always double-quote bash variable expansions to handle paths with spaces.
9. Always confirm the edit by showing modified context after writing.