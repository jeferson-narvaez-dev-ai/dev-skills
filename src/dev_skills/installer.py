"""Core installation logic for dev-skills."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass
from importlib.metadata import distribution
from importlib.resources import files
from pathlib import Path

import click

# ── Constants ────────────────────────────────────────────────
GIT_REPO_URL = "https://github.com/jeferson-narvaez-dev-ai/dev-skills.git"
CONFIG_DIR = Path.home() / ".cache" / "dev-skills"
CONFIG_FILE = CONFIG_DIR / "install.json"
CACHE_DIR = CONFIG_DIR / "repo"


def _detect_install_source() -> tuple[str | None, str | None]:
    """Read PEP 610 direct_url.json to detect repo URL and branch used by uvx/pip."""
    try:
        dist = distribution("dev-skills")
        raw = dist.read_text("direct_url.json")
        if not raw:
            return None, None
        data = json.loads(raw)
        vcs = data.get("vcs_info", {})
        url = data.get("url")
        branch = vcs.get("requested_revision")
        return url, branch
    except Exception:
        return None, None


# ── Styles ──────────────────────────────────────────────────
OK = click.style("[OK]", fg="green")
INFO = click.style("[INFO]", fg="cyan")
WARN = click.style("[WARN]", fg="yellow")
ERROR = click.style("[ERROR]", fg="red")


@dataclass
class InstallConfig:
    """Persisted install configuration."""

    method: str  # "copy" or "symlink"
    scope: str  # "user" or "project"
    clone_path: str | None = None  # absolute path to cloned repo
    version: str | None = None  # git SHA or tag at install time
    branch: str | None = None  # git branch at install time


def _log_ok(msg: str) -> None:
    click.echo(f"  {OK}    {msg}")


def _log_info(msg: str) -> None:
    click.echo(f"  {INFO}  {msg}")


def _log_warn(msg: str) -> None:
    click.echo(f"  {WARN}  {msg}")


def _log_error(msg: str) -> None:
    click.echo(f"  {ERROR} {msg}", err=True)


def _data_path() -> Path:
    """Resolve the bundled data directory (skills, agents, claude-setup).

    In a wheel install, data lives at dev_skills/data/.
    In editable/dev mode, data lives at the repo root (skills/, agents/, claude-setup/).
    """
    # 1. Try wheel-installed path
    pkg = files("dev_skills")
    data = pkg / "data"
    resolved = Path(str(data))
    if resolved.is_dir():
        return resolved

    # 2. Fallback: editable install — repo root has skills/, agents/, claude-setup/
    repo_root = Path(str(pkg)).parent.parent  # src/dev_skills → src → repo root
    if (repo_root / "skills").is_dir() and (repo_root / "agents").is_dir():
        return repo_root

    raise FileNotFoundError(
        f"Bundled data not found at {resolved} or repo root {repo_root}"
    )


class Installer:
    """Orchestrates the installation of skills and agents."""

    def __init__(self, *, dry_run: bool = False) -> None:
        self.dry_run = dry_run
        self._data = _data_path()
        self._scope: str | None = None
        self._tool: str = "claude"
        self._method: str = "copy"
        self._clone_path: Path | None = None
        self._branch: str | None = None
        self._config_dir: Path | None = None
        self._skills_dest: Path | None = None
        self._agents_dest: Path | None = None

    # ── Banner ──────────────────────────────────────────────
    def banner(self) -> None:
        click.echo()
        click.secho("┌──────────────────────────────────────────────────┐", fg="cyan", bold=True)
        click.secho("│   dev-skills — Claude Code & OpenCode Installer   │", fg="cyan", bold=True)
        click.secho("└──────────────────────────────────────────────────┘", fg="cyan", bold=True)
        click.echo()

    # ── Scope ───────────────────────────────────────────────
    def ask_scope(self) -> str:
        tool = self._tool
        if tool == "opencode":
            user_path = "~/.config/opencode/"
            project_path = ".opencode/"
        else:
            user_path = "~/.claude/"
            project_path = ".claude/"
        click.echo("  Where do you want to install?")
        click.echo(f"    1) User level    — {user_path:<24} (available in ALL projects)")
        click.echo(f"    2) Project level — {project_path:<24} (only in the CURRENT project)")
        click.echo()
        choice = click.prompt("  Choose", type=click.Choice(["1", "2"]))
        return "user" if choice == "1" else "project"

    def ask_tool(self) -> str:
        click.echo("  Which AI coding tool?")
        click.echo("    1) Claude Code  — ~/.claude/")
        click.echo("    2) OpenCode     — ~/.config/opencode/")
        click.echo()
        choice = click.prompt("  Choose", type=click.Choice(["1", "2"]))
        tool = "claude" if choice == "1" else "opencode"
        self._tool = tool
        return tool

    def set_tool(self, tool: str) -> None:
        self._tool = tool

    def set_scope(self, scope: str, tool: str = "claude") -> None:
        self._scope = scope
        self._tool = tool
        if tool == "opencode":
            if scope == "user":
                self._config_dir = Path.home() / ".config" / "opencode"
            else:
                self._config_dir = Path.cwd() / ".opencode"
        else:
            if scope == "user":
                self._config_dir = Path.home() / ".claude"
            else:
                self._config_dir = Path.cwd() / ".claude"

        self._skills_dest = self._config_dir / "skills"
        self._agents_dest = self._config_dir / "agents"

    # ── Install method ───────────────────────────────────────
    def ask_method(self) -> str:
        click.echo("  How do you want to install?")
        click.echo("    1) Clone + Symlinks — git clone the repo, symlink skills/agents (auto-updates with git pull)")
        click.echo("    2) Copy             — copy files into ~/.claude/ (traditional)")
        click.echo()
        choice = click.prompt("  Choose", type=click.Choice(["1", "2"]))
        return "symlink" if choice == "1" else "copy"

    def set_method(self, method: str) -> None:
        self._method = method

    def ask_clone_path(self) -> Path:
        default = str(Path.home() / "Documents")
        raw = click.prompt("  Directory where dev-skills will be cloned", default=default)
        return Path(raw).expanduser().resolve()

    def set_clone_path(self, clone_path: Path) -> None:
        self._clone_path = clone_path

    # ── Config persistence ───────────────────────────────────
    @staticmethod
    def find_install_config() -> InstallConfig | None:
        """Load install config from ~/.cache/dev-skills/install.json."""
        if not CONFIG_FILE.exists():
            return None
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            return InstallConfig(**data)
        except (json.JSONDecodeError, TypeError):
            return None

    def save_install_config(self) -> None:
        cfg = InstallConfig(
            method=self._method,
            scope=self._scope or "user",
            clone_path=str(self._clone_path) if self._clone_path else None,
            version=self._get_git_sha(self._clone_path) if self._clone_path else None,
            branch=self._branch,
        )
        if self.dry_run:
            _log_info(f"[DRY-RUN] Would save install config to {CONFIG_FILE}")
            return

        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(
            json.dumps(asdict(cfg), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        _log_ok(f"Install config saved: {CONFIG_FILE}")

    @staticmethod
    def _get_git_sha(repo_path: Path | None) -> str | None:
        if repo_path is None or not (repo_path / ".git").exists():
            return None
        try:
            result = subprocess.run(
                ["git", "-C", str(repo_path), "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    # ── Clone / Pull ─────────────────────────────────────────
    def validate_repo(self, path: Path) -> bool:
        if not (path / ".git").exists():
            return False
        try:
            result = subprocess.run(
                ["git", "-C", str(path), "remote", "-v"],
                capture_output=True,
                text=True,
                check=True,
            )
            return "dev-skills" in result.stdout
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _resolve_clone_path(self, clone_path: Path) -> Path:
        """Resolve the final clone directory.

        If the path is an existing directory without .git/, treat it as
        the parent and append 'dev-skills' (e.g. ~/Documents → ~/Documents/dev-skills).
        If it already IS a git repo or doesn't exist, use it as-is.
        """
        if clone_path.exists() and clone_path.is_dir() and not (clone_path / ".git").exists():
            resolved = clone_path / "dev-skills"
            _log_info(f"Clone target resolved to: {resolved}")
            return resolved
        return clone_path

    def clone_or_pull(
        self,
        clone_path: Path,
        repo_url: str | None = None,
        branch: str | None = None,
    ) -> Path:
        """Clone or pull the repo. Returns the final clone path (may differ from input)."""
        detected_url, detected_branch = _detect_install_source()
        url = repo_url or detected_url or GIT_REPO_URL
        branch = branch or detected_branch or "main"
        self._branch = branch

        click.secho("\n  Setting up clone...", bold=True)
        _log_info(f"Repo   : {url}")
        _log_info(f"Branch : {branch}")

        clone_path = self._resolve_clone_path(clone_path)

        if clone_path.exists():
            has_git = (clone_path / ".git").exists()

            if has_git and self.validate_repo(clone_path):
                if self.dry_run:
                    _log_info(f"[DRY-RUN] Would git pull in {clone_path} (branch: {branch})")
                    return clone_path

                _log_info(f"Existing repo found at {clone_path} — pulling latest...")
                subprocess.run(["git", "-C", str(clone_path), "fetch", "origin"], check=True)
                subprocess.run(["git", "-C", str(clone_path), "checkout", branch], check=True)
                subprocess.run(["git", "-C", str(clone_path), "pull", "origin", branch], check=True)
                _log_ok(f"Updated: {clone_path} (branch: {branch})")
                return clone_path

            if has_git:
                _log_error(
                    f"{clone_path} is a git repo but not dev-skills. "
                    "Choose a different --clone-path."
                )
                raise click.Abort()

            _log_error(
                f"{clone_path} already exists and is not a git repository. "
                "Remove it or choose a different path."
            )
            raise click.Abort()

        if self.dry_run:
            _log_info(f"[DRY-RUN] Would git clone {url} -b {branch} → {clone_path}")
            return clone_path

        _log_info(f"Cloning {url} → {clone_path}...")
        clone_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "-b", branch, url, str(clone_path)], check=True)
        _log_ok(f"Cloned: {clone_path} (branch: {branch})")
        return clone_path

    # ── Symlink helpers ──────────────────────────────────────
    def _create_symlink(self, src: Path, dest: Path, *, is_dir: bool = False) -> None:
        if self.dry_run:
            _log_info(f"[DRY-RUN] Would symlink {dest} → {src}")
            return

        if dest.is_symlink() or dest.exists():
            if dest.is_dir() and not dest.is_symlink():
                shutil.rmtree(dest)
            else:
                dest.unlink()

        os.symlink(src, dest, target_is_directory=is_dir)

    def install_skills_symlink(self, clone_path: Path) -> None:
        click.secho("\n  Linking skills...", bold=True)
        src = clone_path / "skills"
        if not src.is_dir():
            _log_warn("No skills directory found in clone — skipping.")
            return

        self._skills_dest.parent.mkdir(parents=True, exist_ok=True)
        self._create_symlink(src, self._skills_dest, is_dir=True)
        if not self.dry_run:
            count = sum(1 for d in src.iterdir() if d.is_dir())
            _log_ok(f"Linked: {self._skills_dest} → {src} ({count} skills)")

    def install_agents_symlink(self, clone_path: Path) -> None:
        click.secho("\n  Linking agents...", bold=True)
        src = clone_path / "agents"
        if not src.is_dir():
            _log_warn("No agents directory found in clone — skipping.")
            return

        self._agents_dest.parent.mkdir(parents=True, exist_ok=True)
        self._create_symlink(src, self._agents_dest, is_dir=True)
        if not self.dry_run:
            count = sum(1 for f in src.glob("*.md"))
            _log_ok(f"Linked: {self._agents_dest} → {src} ({count} agents)")

    def show_summary(self, *, full: bool = True) -> None:
        """Show install plan."""
        method_label = "symlink (clone + link)" if self._method == "symlink" else "copy"
        if full:
            tool = self._tool or "claude"
            if tool == "opencode":
                user_dir, project_dir = "~/.config/opencode/", ".opencode/"
            else:
                user_dir, project_dir = "~/.claude/", ".claude/"
            if self._scope == "user":
                label = f"user ({user_dir}) [{tool}]"
            else:
                label = f"project ({Path.cwd()}/{project_dir.rstrip('/')}) [{tool}]"
            _log_info(f"Scope        : {click.style(label, bold=True)}")
        _log_info(f"Method       : {click.style(method_label, bold=True)}")
        if self._clone_path:
            _log_info(f"Clone path   : {self._clone_path}")
        if full:
            _log_info(f"Skills  → : {self._skills_dest}")
            _log_info(f"Agents  → : {self._agents_dest}")
        click.echo()

    def _done_banner(self, text: str) -> None:
        """Print dry-run or success banner."""
        click.echo()
        if self.dry_run:
            click.secho("  ✓ Dry run complete — no changes were made.", fg="yellow", bold=True)
        else:
            click.secho(f"  ✓ {text}", fg="green", bold=True)
        click.echo()

    def done_install(self) -> None:
        """Post-install message for the install command."""
        self._done_banner("Source ready.")
        if self._clone_path:
            click.echo(f"  Source : {self._clone_path}")
        click.echo(f"  Method : {click.style(self._method, bold=True)}")
        click.echo(f"  CLI    : dev-skills (installed globally)")
        click.echo()
        click.echo("  Next step — add skills to a project:")
        click.echo(f"    uvx dev-skills add --scope user")
        click.echo(f"    uvx dev-skills add skills --scope project")
        click.echo(f"    uvx dev-skills add --scope user --tool opencode")
        click.echo()

    # ── Skills ──────────────────────────────────────────────
    def install_skills(self, *, force: bool = False, source: Path | None = None) -> None:
        click.secho("\n  Installing skills...", bold=True)
        src = (source or self._data) / "skills"
        if not src.is_dir():
            _log_warn("No skills directory found in package data — skipping.")
            return

        installed, updated = 0, 0
        if not self.dry_run:
            self._skills_dest.mkdir(parents=True, exist_ok=True)

        for skill_dir in sorted(src.iterdir()):
            if not skill_dir.is_dir():
                continue
            dest = self._skills_dest / skill_dir.name
            is_update = dest.exists()

            if self.dry_run:
                action = "update" if is_update else "install"
                _log_info(f"[DRY-RUN] Would {action} skill: {skill_dir.name}")
            else:
                if is_update:
                    shutil.rmtree(dest)
                shutil.copytree(skill_dir, dest)
                if is_update:
                    _log_ok(f"Updated  skill: {skill_dir.name}")
                    updated += 1
                else:
                    _log_ok(f"Installed skill: {skill_dir.name}")
                    installed += 1

        if not self.dry_run:
            _log_info(f"Skills: {installed} new, {updated} updated.")

    # ── Agents ──────────────────────────────────────────────
    def install_agents(self, *, force: bool = False, source: Path | None = None) -> None:
        click.secho("\n  Installing agents...", bold=True)
        src = (source or self._data) / "agents"
        if not src.is_dir():
            _log_warn("No agents directory found in package data — skipping.")
            return

        installed, updated = 0, 0
        if not self.dry_run:
            self._agents_dest.mkdir(parents=True, exist_ok=True)

        for agent_file in sorted(src.glob("*.md")):
            dest = self._agents_dest / agent_file.name
            is_update = dest.exists()

            if self.dry_run:
                action = "update" if is_update else "install"
                _log_info(f"[DRY-RUN] Would {action} agent: {agent_file.name}")
            else:
                shutil.copy2(agent_file, dest)
                if is_update:
                    _log_ok(f"Updated  agent: {agent_file.name}")
                    updated += 1
                else:
                    _log_ok(f"Installed agent: {agent_file.name}")
                    installed += 1

        if not self.dry_run:
            _log_info(f"Agents: {installed} new, {updated} updated.")

    # ── Install all ──────────────────────────────────────────
    def install_all(self, source: Path, *, force: bool = False) -> None:
        """Install all components, dispatching symlink vs copy based on method."""
        if self._method == "symlink":
            self.install_skills_symlink(source)
            self.install_agents_symlink(source)
        else:
            self.install_skills(force=force, source=source)
            self.install_agents(force=force, source=source)

    # ── Global CLI install ────────────────────────────────
    def install_cli(self, clone_path: Path) -> None:
        """Install dev-skills CLI globally via uv tool install."""
        click.secho("\n  Installing CLI globally...", bold=True)

        if self.dry_run:
            _log_info(f"[DRY-RUN] Would run: uv tool install {clone_path}")
            return

        try:
            subprocess.run(
                ["uv", "tool", "install", "--force", str(clone_path)],
                check=True,
            )
            _log_ok("CLI installed globally — you can now use 'dev-skills' directly.")
        except (subprocess.CalledProcessError, FileNotFoundError):
            _log_warn(
                "Could not install CLI globally. You can do it manually:\n"
                f"    uv tool install {clone_path}"
            )

    # ── Uninstall ──────────────────────────────────────────
    def _remove_path(self, path: Path | None) -> None:
        """Remove a file or directory, handling symlinks and dry-run."""
        if not path or not (path.exists() or path.is_symlink()):
            return
        if self.dry_run:
            _log_info(f"[DRY-RUN] Would remove {path}")
            return
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink()
        _log_ok(f"Removed: {path}")

    def uninstall(self) -> None:
        """Remove installed skills and agents for the current scope."""
        click.secho("\n  Uninstalling...", bold=True)
        self._remove_path(self._skills_dest)
        self._remove_path(self._agents_dest)
        self._done_banner("Uninstall complete.")

    # ── Status ────────────────────────────────────────────
    @staticmethod
    def _status_block(label: str, skills_dir: Path, agents_dir: Path) -> None:
        """Print a single status block for a scope combination."""
        skill_count = sum(1 for _ in skills_dir.iterdir()) if skills_dir.is_dir() else 0
        agent_count = sum(1 for _ in agents_dir.glob("*.md")) if agents_dir.is_dir() else 0

        if skill_count == 0 and agent_count == 0:
            click.echo(f"  [{label}] not installed")
        else:
            click.echo(f"  [{label}]")
            click.echo(f"    Skills    : {skill_count} installed" if skill_count else "    Skills    : —")
            click.echo(f"    Agents    : {agent_count} installed" if agent_count else "    Agents    : —")
        click.echo()

    @classmethod
    def status(cls) -> None:
        """Show installation status."""
        click.echo()
        click.secho("  dev-skills — Status", bold=True)
        click.echo()

        config = cls.find_install_config()
        if config is None:
            click.echo("  Not installed. Run: uvx dev-skills install")
            click.echo()
            return

        method_label = "symlink (clone + link)" if config.method == "symlink" else "copy"
        click.echo(f"  Method     : {click.style(method_label, bold=True)}")
        if config.clone_path:
            click.echo(f"  Clone path : {config.clone_path}")
        if config.branch:
            click.echo(f"  Branch     : {config.branch}")
        if config.version:
            click.echo(f"  Version    : {config.version}")
        click.echo()

        click.secho("  Claude Code", bold=True)
        click.echo()
        for scope_name, config_dir in [
            ("user", Path.home() / ".claude"),
            ("project", Path.cwd() / ".claude"),
        ]:
            cls._status_block(
                f"claude/{scope_name}",
                config_dir / "skills",
                config_dir / "agents",
            )

        click.secho("  OpenCode", bold=True)
        click.echo()
        for scope_name, config_dir in [
            ("user", Path.home() / ".config" / "opencode"),
            ("project", Path.cwd() / ".opencode"),
        ]:
            cls._status_block(
                f"opencode/{scope_name}",
                config_dir / "skills",
                config_dir / "agents",
            )

    # ── Done ────────────────────────────────────────────────
    def done(self) -> None:
        tool = self._tool or "claude"
        self._done_banner(f"Installation complete ({tool}).")
        click.echo(f"  Tool      : {click.style(tool, bold=True)}")
        click.echo(f"  Method    : {click.style(self._method, bold=True)}")
        if self._clone_path:
            click.echo(f"  Source    : {self._clone_path}")
        click.echo(f"  Skills    : {self._skills_dest}")
        click.echo(f"  Agents    : {self._agents_dest}")
        click.echo()
        if self._method == "symlink":
            click.echo("  To update skills/agents instantly:")
            click.echo(f"    cd {self._clone_path} && " + click.style("git pull", bold=True))
            click.echo()
        click.echo("  Quick commands:")
        click.echo("    uvx dev-skills add skills                     — install skills to a project")
        click.echo("    uvx dev-skills add agents                     — install agents to a project")
        click.echo()
