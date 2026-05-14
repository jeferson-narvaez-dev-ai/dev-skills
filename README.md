# dev-skills

Personal Claude Code skills collection — Obsidian integration and dev utilities.

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
uvx --from "git+https://github.com/jnarvaezp/dev-skills.git@main" dev-skills install

# Add skills to Claude Code (user level)
uvx dev-skills add --scope user

# Configure vault paths in ~/.claude/settings.json
# Add: "VAULT_FOLDER": "/path/to/your/vault"
# Add: "PROJECTS_FOLDER": "/path/to/your/projects"
```

See [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md) for full details.
