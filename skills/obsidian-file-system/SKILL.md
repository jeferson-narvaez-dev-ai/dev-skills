---
name: obsidian-file-system
description: >
  Canonical file system layout for the Obsidian vault and project repositories.
  Load this skill whenever any obsidian skill needs to resolve paths.
license: MIT
metadata:
  author: jeferson narvaez
  version: "3.0"
---

## Purpose

Single source of truth for all path resolution across Obsidian skills. Every obsidian skill must load this skill first and use the variables defined here.

---

## Two Worlds

| Variable | Env key | Absolute path | Purpose |
|----------|---------|---------------|---------|
| `VAULT` | `VAULT_FOLDER` | `/Users/jeferson.narvaez/Documents/Development/kushki-brain/kushki-docs-obsidian` | Obsidian vault — documentation only |
| `PROJECTS` | `PROJECTS_FOLDER` | `/Users/jeferson.narvaez/Documents/Development/kushki-brain/Kushki` | Source code repositories |

**Rule: never mix them.** Documentation goes in `$VAULT`. Source code goes in `$PROJECTS`. Nothing from `$PROJECTS` goes inside `$VAULT` and vice versa.

---

## Resolution Block

Every obsidian skill must execute this block before any file operation:

```bash
VAULT="${VAULT_FOLDER:?'VAULT_FOLDER is not set — add it to ~/.claude/settings.json env section'}"
PROJECTS="${PROJECTS_FOLDER:?'PROJECTS_FOLDER is not set — add it to ~/.claude/settings.json env section'}"
```

---

## Vault Structure

Documentation only. Projects go directly under the vault root — no intermediate subfolder.

```
$VAULT_FOLDER/
├── {project-name}/              ← one folder per project, named after git repo
│   └── {branch-folder}/        ← git branch with "/" replaced by "-"
│       ├── exploration/        ← research, code reading, understanding flows
│       ├── plan/               ← implementation plans
│       ├── issue/              ← bug analysis, incidents, production problems
│       ├── implementation/     ← progress notes, decisions during development
│       └── review/             ← PR reviews, post-mortems, retrospectives
│
├── general/                    ← for notes not tied to a specific repo
└── Documentation/              ← legacy folder, do NOT use for new notes
```

## Projects Structure

Source code only. Never put documentation here.

```
$PROJECTS_FOLDER/
├── usrv-card/
├── usrv-cash/
├── usrv-transfer/
├── usrv-acq-ecommerce/
└── {project-name}/
```

---

## Path Construction

### Derive project and branch from git (run inside a repo)

```bash
PROJECT=$(basename "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null || echo "general")
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")
BRANCH_FOLDER="${BRANCH//\//-}"
DATE=$(date +%Y-%m-%d)
```

### Build a documentation note path

```bash
NOTE_PATH="$VAULT/$PROJECT/$BRANCH_FOLDER/{type}/{name}-$DATE.md"
```

### Build a canvas path

```bash
CANVAS_PATH="$VAULT/$PROJECT/$BRANCH_FOLDER/{type}/{name}-$DATE.canvas"
```

### Build a source code path

```bash
SOURCE_PATH="$PROJECTS/{project-name}/"
```

---

## Branch Naming

| Branch type | Pattern | Folder name |
|-------------|---------|-------------|
| Feature | `feature/CAR-001` | `feature-CAR-001` |
| Release | `release/1.2.3` | `release-1.2.3` |
| Hotfix | `hotfix/fix-timeout` | `hotfix-fix-timeout` |
| Main | `main` | `main` |
| Master | `master` | `master` |
| Develop | `develop` | `develop` |

**Rule:** replace `/` with `-` in branch name to get folder name.

---

## Doc Type Guide

| Folder | Use when |
|--------|----------|
| `exploration/` | First contact with a codebase, understanding an existing flow, researching options |
| `plan/` | Designing a solution, writing an implementation plan after exploration |
| `issue/` | Investigating a bug, analyzing a production incident, root-cause analysis |
| `implementation/` | Taking notes while coding, recording decisions made during a PR |
| `review/` | Reviewing a PR, writing a retrospective, post-mortem |

**Natural flow:** `exploration` → `plan` → `implementation` (parallel: `issue` for bugs, `review` for PRs)

---

## Where to Search

| Task | Where to look |
|------|--------------|
| Find docs for a project | `$VAULT/{project}/` |
| Find docs for a specific branch | `$VAULT/{project}/{branch-folder}/` |
| Find exploration notes | `$VAULT/{project}/{branch-folder}/exploration/` |
| Find latest plan | `$VAULT/{project}/{branch-folder}/plan/` — sort by date desc |
| Find a PR review | `$VAULT/{project}/{branch-folder}/review/` |
| Find an incident note | `$VAULT/{project}/*/issue/` |
| Search across all docs | Search recursively under `$VAULT/` |
| List all documented projects | `ls $VAULT/` |
| Find source code for a project | `$PROJECTS/{project-name}/` |
| List all available repos | `ls $PROJECTS/` |

---

## File Naming

```
{descriptive-name}-{YYYY-MM-DD}.md
{descriptive-name}-{YYYY-MM-DD}.canvas
```

- Use kebab-case
- Always append the date so files sort chronologically
- A `.canvas` and `.md` with the same base name in the same folder are a **linked pair**

---

## Rules

1. Always execute the resolution block before any file operation.
2. `$VAULT` is for documentation only — never put source code there.
3. `$PROJECTS` is for source code only — never put documentation there.
4. Projects go directly under `$VAULT/{project}/` — no intermediate subfolder.
5. Never use the `Documentation/` folder for new notes — it is legacy.
6. Branch folder name = branch name with `/` replaced by `-`.
7. When not inside a git repo, use `general` as project name and `main` as branch.
8. Canvas and markdown files with the same base name are a linked pair — always maintain both.
