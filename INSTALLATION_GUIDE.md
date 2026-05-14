# Installation Guide — dev-skills

## Requirements

- Python >= 3.10
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Git

## 1. Configure vault paths

Before using any Obsidian skills, add these environment variables to `~/.claude/settings.json`:

```json
{
  "env": {
    "VAULT_FOLDER": "/path/to/your/obsidian-vault",
    "PROJECTS_FOLDER": "/path/to/your/projects"
  }
}
```

A template is available at `claude-setup/settings.sample.json`.

## 2. Install CLI and clone the repo (one-time setup)

```bash
uvx --from "git+https://github.com/jnarvaezp/dev-skills.git@main" dev-skills install
```

This will:
- Clone the repo to `~/.cache/dev-skills/repo` (copy mode) or a directory you choose (symlink mode)
- Install the `dev-skills` CLI globally via `uv tool install`
- Save the install configuration to `~/.cache/dev-skills/install.json`

### Install options

```bash
# Symlink mode (recommended for easy updates)
uvx ... dev-skills install --link --clone-path ~/Documents/GitHub/dev-skills

# Copy mode (default)
uvx ... dev-skills install --copy

# Dry run (preview without changes)
uvx ... dev-skills install --dry-run
```

## 3. Add skills to Claude Code

```bash
# User level — available in ALL projects
uvx dev-skills add --scope user

# Project level — only in the current project
uvx dev-skills add --scope project

# Skills only
uvx dev-skills add skills --scope user

# Agents only
uvx dev-skills add agents --scope user
```

## 4. Additional commands

### Update

```bash
# Update source repo only
uvx dev-skills update

# Update and re-install to user scope
uvx dev-skills update --scope user
```

### Uninstall

```bash
# Remove from user scope
uvx dev-skills uninstall --scope user

# Remove from project scope
uvx dev-skills uninstall --scope project
```

### Status

```bash
uvx dev-skills status
```

## Troubleshooting

**Skills not found after install**
- Verify `~/.claude/skills/` exists and contains the skill directories.
- Run `uvx dev-skills status` to see what is installed and where.

**Vault env vars not picked up**
- Ensure `VAULT_FOLDER` and `PROJECTS_FOLDER` are set in `~/.claude/settings.json` under the `env` key (not your shell profile).
- Restart Claude Code after editing `settings.json`.

**CLI not found after install**
- Ensure `~/.local/bin` (or wherever `uv tool` installs) is in your `$PATH`.
- Run `uv tool list` to verify `dev-skills` is listed.

**"Source not found" error on `add`**
- The clone path recorded during `install` no longer exists. Re-run `uvx ... dev-skills install` to re-clone.
