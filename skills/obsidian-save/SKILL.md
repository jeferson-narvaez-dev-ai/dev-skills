---
name: obsidian-save
description: >
  Creates or overwrites a note in an Obsidian vault. Resolves the vault path from environment or config.
  Trigger: When the user wants to save, create, write, or overwrite a note in Obsidian. Examples: "save note to obsidian", "create obsidian note", "write to vault", "/obsidian-save".
license: MIT
metadata:
  author: jeferson narvaez
  version: "2.0"
---

## Purpose

Create or overwrite a Markdown note in an Obsidian vault. Automatically resolves the repo name, git branch, current date, and note type to build a structured path. Supports optional YAML frontmatter and ensures parent directories are created automatically.

---

## Vault Resolution

Load `obsidian-file-system` skill first — it is the single source of truth for all paths and defines `$VAULT` and `$PROJECTS`.

- `$VAULT` — absolute path to the Obsidian vault (documentation only)
- `$PROJECTS` — absolute path to source code repositories

All note paths follow: `$VAULT/{project}/{branch-folder}/{type}/{name}-{date}.md`

---

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `note_name` | Yes | — | Short name for the note (e.g. `Plan AI15190 TID`). Do NOT include date or path — those are resolved automatically. |
| `content` | Yes | — | Markdown body for the note. |
| `note_type` | No | *(ask user)* | One of: `exploration`, `plan`, `issue`, `implementation`, `review`. If not provided, ask the user before proceeding. |
| `note_path` | No | *(auto-resolved)* | Override the full relative path from vault root. If provided, skips all auto-resolution logic. |
| `frontmatter` | No | — | YAML key-value pairs to prepend as a frontmatter block. |
| `overwrite` | No | `true` | If `false` and the file already exists, abort and notify the user instead of overwriting. |

---

## Note Type Taxonomy

Always ask the user which type applies if `note_type` is not provided:

| Type | When to use | Path pattern |
|------|------------|--------------|
| `exploration` | Initial research, code analysis, understanding how something works | `{project}/{branch}/exploration/{name}-{date}.md` |
| `plan` | Implementation plan based on prior exploration | `{project}/{branch}/plan/{name}-{date}.md` |
| `issue` | Bug analysis, incidents, production problems | `{project}/{branch}/issue/{name}-{date}.md` |
| `implementation` | Progress notes while implementing, decisions made during development | `{project}/{branch}/implementation/{name}-{date}.md` |
| `review` | PR reviews, post-mortems, retrospectives | `{project}/{branch}/review/{name}-{date}.md` |

**Natural flow:** `exploration` → `plan` → `implementation` (with `issue` for bugs, `review` for PR/retrospectives)

---

## Steps

### 1. Resolve vault path

Use the vault resolution logic above.

### 2. Ask for note type (if not provided)

If `note_type` was not supplied, ask the user:

```
What type of note is this?
  1. exploration    — research / code analysis
  2. plan           — implementation plan
  3. issue          — bug analysis / incident / production problem
  4. implementation — in-progress development notes
  5. review         — PR review / post-mortem / retrospective

Enter number or name:
```

### 3. Resolve project name, branch, and date

```bash
PROJECT=$(basename "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null || echo "general")
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")
DATE=$(date +%Y-%m-%d)
```

### 4. Build note path (if not overridden)

If `note_path` was not explicitly provided, build it from type:

```bash
NOTE_NAME="{note_name}"

case "{note_type}" in
  exploration)    RELATIVE_PATH="${PROJECT}/${BRANCH}/exploration/${NOTE_NAME}-${DATE}.md" ;;
  plan)           RELATIVE_PATH="${PROJECT}/${BRANCH}/plan/${NOTE_NAME}-${DATE}.md" ;;
  issue)          RELATIVE_PATH="${PROJECT}/${BRANCH}/issue/${NOTE_NAME}-${DATE}.md" ;;
  implementation) RELATIVE_PATH="${PROJECT}/${BRANCH}/implementation/${NOTE_NAME}-${DATE}.md" ;;
  review)         RELATIVE_PATH="${PROJECT}/${BRANCH}/review/${NOTE_NAME}-${DATE}.md" ;;
esac

NOTE="$VAULT/$RELATIVE_PATH"
```

### 5. Check overwrite flag

If `overwrite` is `false` and the file already exists, stop and inform the user:

```bash
if [ "{overwrite}" = "false" ] && [ -f "$NOTE" ]; then
  echo "Note already exists at: $NOTE"
  echo "Set overwrite=true to replace it."
  exit 1
fi
```

### 6. Create parent directories

```bash
mkdir -p "$(dirname "$NOTE")"
```

### 7. Write the file

If `frontmatter` key-value pairs are provided, prepend a YAML frontmatter block using Python3:

```bash
python3 - <<'PYEOF'
note_path = "{resolved NOTE path}"
frontmatter = {frontmatter_dict_or_None}
content = """{content}"""

lines = []
if frontmatter:
    lines.append("---")
    for k, v in frontmatter.items():
        lines.append(f"{k}: {v}")
    lines.append("---")
    lines.append("")

lines.append(content)

with open(note_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"Written: {note_path}")
PYEOF
```

If no frontmatter is provided, write the content directly:

```bash
printf '%s' "{content}" > "$NOTE"
```

### 8. Confirm with file path and size

```bash
SIZE=$(wc -c < "$NOTE")
echo "Note saved: $NOTE ($SIZE bytes)"
```

---

## Canvas Linking

### When saving a note

After writing the `.md` file, check if a `.canvas` file with the same base name exists in the same folder:

```bash
CANVAS_SIBLING="${NOTE_PATH%.md}.canvas"
```

1. If it **exists** → append this block to the note (if not already present):

   ```markdown
   ---
   ## 🗺 Canvas
   ![[{base-name}.canvas]]
   ```

2. If it does **NOT exist** → add this to the note's YAML frontmatter:

   ```yaml
   canvas: ""
   ```

   So the author can fill it in manually later.

### When a canvas name is explicitly provided by the user

- Set the frontmatter `canvas` field to `"[[{canvas-name}.canvas]]"`
- Embed the canvas at the bottom of the note body with `![[{canvas-name}.canvas]]`

---

## Rules

1. Always resolve vault before any file operation.
2. Always ask for `note_type` if not provided — never assume.
3. Always auto-append `.md` if the extension is missing.
4. Date format is always `YYYY-MM-DD` appended at the end of the filename, before `.md`.
5. All note types include the git branch in the path (under `$VAULT/$PROJECT/$BRANCH/`). Projects go directly under `$VAULT/` — no intermediate subfolder.
6. If not inside a git repo, use `"general"` as project name and `"main"` as branch.
7. Never use `import yaml` — PyYAML is not stdlib. Build the frontmatter block with plain string formatting.
8. Always double-quote bash variable expansions to handle paths with spaces.
9. If `overwrite` is `false` and the file exists, abort gracefully with a clear message.
10. Confirm success by displaying the full file path and byte size.
11. Canvas and markdown notes with the same base name in the same folder are treated as a linked pair — always check for and maintain the sibling link.
12. Never put source code inside `$VAULT` — it belongs in `$PROJECTS`.
13. Never put documentation files inside `$PROJECTS` — docs go in `$VAULT`.
