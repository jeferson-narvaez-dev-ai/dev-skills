---
name: obsidian-list-files
description: >
  Lists all files in the Obsidian vault directory that corresponds to the current project and branch. Uses the same path resolution logic as obsidian-save: /{vault}/{repo}/{type}/ for git repos, or /{vault}/{date}/ for non-git.
  Trigger: When the user wants to see, list, or browse files saved in Obsidian for the current project. Examples: "list obsidian files", "show my obsidian notes", "what's in obsidian", "/obsidian-list-files".
license: MIT
metadata:
  author: jeferson narvaez
  version: "2.0"
---

## Purpose

List all files in the Obsidian vault directory for the current project. Uses the exact same path resolution taxonomy as `obsidian-save` v2.0 so listed paths always match where notes are saved.

## Note Type Taxonomy

| Type | Path pattern |
|------|-------------|
| `exploration` | `{project}/{branch}/exploration/` |
| `plan` | `{project}/{branch}/plan/` |
| `issue` | `{project}/{branch}/issue/` |
| `implementation` | `{project}/{branch}/implementation/` |
| `review` | `{project}/{branch}/review/` |
| *(all)* | `{project}/{branch}/` — lists everything |

---

## Vault Resolution

Load `obsidian-file-system` skill first — it is the single source of truth for all paths and defines `$VAULT` and `$PROJECTS`.

- `$VAULT` — absolute path to the Obsidian vault (documentation only)
- `$PROJECTS` — absolute path to source code repositories

All note paths follow: `$VAULT/{project}/{branch-folder}/{type}/{name}-{date}.md`
Consult `obsidian-file-system` for vault structure, branch naming, and path construction.

---

## Steps

### 1. Resolve vault path

Use the vault resolution logic above.

### 2. Resolve project name and branch

```bash
PROJECT=$(basename "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null || echo "general")
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")
```

### 3. Ask for note type (optional filter)

Ask the user which type to list, or all:

```
Which notes do you want to list?
  1. exploration
  2. plan
  3. issue
  4. implementation
  5. review
  6. all  (current branch: {branch})

Enter number or name (default: all):
```

### 4. Build target directory

```bash
case "{note_type}" in
  exploration)    TARGET_DIR="$VAULT/$PROJECT/$BRANCH/exploration" ;;
  plan)           TARGET_DIR="$VAULT/$PROJECT/$BRANCH/plan" ;;
  issue)          TARGET_DIR="$VAULT/$PROJECT/$BRANCH/issue" ;;
  implementation) TARGET_DIR="$VAULT/$PROJECT/$BRANCH/implementation" ;;
  review)         TARGET_DIR="$VAULT/$PROJECT/$BRANCH/review" ;;
  *)              TARGET_DIR="$VAULT/$PROJECT/$BRANCH" ;;
esac
```

### 5. Check if directory exists

```bash
if [ ! -d "$TARGET_DIR" ]; then
  echo "Directory does not exist: $TARGET_DIR"
  echo "No notes saved for this project/type yet."
  exit 0
fi
```

### 6. List all files with metadata

```bash
python3 - <<'PYEOF'
import os

target_dir = "{resolved TARGET_DIR}"
vault = "{resolved VAULT}"

if not os.path.isdir(target_dir):
    print(f"Directory does not exist: {target_dir}")
else:
    entries = []
    for root, dirs, files in os.walk(target_dir):
        dirs.sort()
        files.sort()
        for fname in files:
            full_path = os.path.join(root, fname)
            rel_path = os.path.relpath(full_path, vault)
            size = os.path.getsize(full_path)
            ext = os.path.splitext(fname)[1].lower()
            ftype = "Markdown note" if ext == ".md" else "Canvas" if ext == ".canvas" else "File"
            entries.append((rel_path, ftype, size))

    if not entries:
        print(f"Directory exists but is empty: {target_dir}")
    else:
        print(f"Notes in: {target_dir}\n")
        print(f"{'Name':<60} {'Type':<16} {'Size':>8}")
        print("-" * 86)
        for rel_path, ftype, size in entries:
            size_str = f"{size} B" if size < 1024 else f"{size // 1024} KB"
            print(f"{rel_path:<60} {ftype:<16} {size_str:>8}")
        print(f"\nTotal: {len(entries)} file(s)")
PYEOF
```

---

## Rules

1. Always resolve vault before any file operation.
2. Use the same path taxonomy as `obsidian-save` — `$VAULT/$PROJECT/$BRANCH/{type}/` structure. Projects go directly under `$VAULT/` — no intermediate subfolder.
3. Project name is always `basename` of the git root. Falls back to `"general"` if not a git repo.
4. All note types include the branch in the path (under `$VAULT/$PROJECT/$BRANCH/`).
5. If the directory does not exist, report clearly — do NOT treat it as an error.
6. Always show the full resolved path so the user can verify it.
7. Always double-quote bash variable expansions to handle paths with spaces.