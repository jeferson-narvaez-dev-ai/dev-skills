# dev-skills

Personal AI coding skills collection — Obsidian integration and dev utilities. Supports **Claude Code** and **OpenCode**.

## Skills included

| Skill | Description |
|-------|-------------|
| `obsidian-file-system` | Canonical vault path resolution — load this first |
| `obsidian-save` | Create or overwrite notes in the vault |
| `obsidian-get` | Read notes with frontmatter parsing |
| `obsidian-edit` | Append, prepend, or replace content in notes |
| `obsidian-delete` | Delete notes with confirmation |
| `obsidian-search` | Full-text and frontmatter search |
| `obsidian-list-files` | List notes by project and branch |
| `obsidian-canvas` | Create and manage canvas files |

## Quick start

```bash
# Install CLI + clone repo (one time)
uvx --from "git+https://github.com/jeferson-narvaez-dev-ai/dev-skills.git@main" dev-skills install

# Add skills to Claude Code (user level)
uvx dev-skills add --scope user

# Add skills to OpenCode (user level)
uvx dev-skills add --scope user --tool opencode

# Configure vault paths in ~/.claude/settings.json (Claude Code)
# Add: "VAULT_FOLDER": "/path/to/your/vault"
# Add: "PROJECTS_FOLDER": "/path/to/your/projects"

# Configure vault paths for OpenCode — copy the sample and edit it
# cp opencode-setup/opencode.json.sample ~/.config/opencode/opencode.json
# Then set VAULT_FOLDER and PROJECTS_FOLDER in your shell profile
```

See [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md) for full details.
