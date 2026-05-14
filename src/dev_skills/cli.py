"""CLI entry point for uvx dev-skills installer."""

from pathlib import Path

import click

from dev_skills import __version__
from dev_skills.installer import CACHE_DIR, Installer

# ── Shared option decorators ──────────────────────────────
_scope_option = click.option(
    "--scope",
    type=click.Choice(["user", "project"], case_sensitive=False),
    default=None,
    help="Install scope: user (~/.claude/) or project (.claude/).",
)
_tool_option = click.option(
    "--tool",
    type=click.Choice(["claude", "opencode"], case_sensitive=False),
    default=None,
    help="Target tool: claude (~/.claude/) or opencode (~/.config/opencode/).",
)
_force_option = click.option("--force", is_flag=True, help="Overwrite existing files without prompting.")
_dry_run_option = click.option("--dry-run", is_flag=True, help="Show what would be done without making changes.")


@click.group()
@click.version_option(version=__version__, prog_name="dev-skills")
def main() -> None:
    """dev-skills — Claude Code installer for personal dev utilities."""


# ── Shared helpers ─────────────────────────────────────────
def _require_config() -> tuple:
    """Load saved config and return (config, clone_path). Aborts if missing."""
    config = Installer.find_install_config()
    if config is None or not config.clone_path:
        click.secho("  No installation found. Run `uvx dev-skills install` first.", fg="red", err=True)
        raise SystemExit(1)

    clone_path = Path(config.clone_path)
    if not clone_path.exists() or not (clone_path / ".git").exists():
        click.secho(
            f"  Source not found at {clone_path}. Run `uvx dev-skills install` again.",
            fg="red",
            err=True,
        )
        raise SystemExit(1)

    return config, clone_path


def _make_installer(config, clone_path: Path, *, dry_run: bool, scope: str | None, tool: str | None = None) -> Installer:
    """Create an Installer pre-configured from saved config + scope."""
    installer = Installer(dry_run=dry_run)
    installer.set_method(config.method)
    installer.set_clone_path(clone_path)
    if tool is None:
        installer.ask_tool()
    else:
        installer.set_tool(tool)
    if scope is None:
        scope = installer.ask_scope()
    installer.set_scope(scope, installer._tool)
    return installer


# ── install ──────────────────────────────────────────────────
@main.command()
@click.option("--link", "method", flag_value="symlink", help="Install via git clone + symlinks.")
@click.option("--copy", "method", flag_value="copy", help="Install via file copy (default).")
@click.option("--clone-path", type=click.Path(), default=None, help="Directory where the repo will be cloned.")
@click.option("--repo-url", default=None, help="Git repo URL to clone.")
@click.option("--branch", default=None, help="Git branch to clone/checkout (auto-detected from uvx source).")
@_dry_run_option
def install(
    method: str | None,
    clone_path: str | None,
    repo_url: str | None,
    branch: str | None,
    dry_run: bool,
) -> None:
    """Get the source code and install the CLI (one-time setup)."""
    installer = Installer(dry_run=dry_run)
    installer.banner()

    # 1. How to install (method)
    if method is None:
        method = installer.ask_method()
    installer.set_method(method)

    # 2. Resolve clone path
    if method == "symlink":
        resolved_clone = Path(clone_path).expanduser().resolve() if clone_path else installer.ask_clone_path()
    else:
        resolved_clone = Path(clone_path).expanduser().resolve() if clone_path else CACHE_DIR
    installer.set_clone_path(resolved_clone)

    # 3. Show summary and confirm
    installer.show_summary(full=False)
    if not dry_run:
        click.confirm("  Proceed?", abort=True)

    # 4. Clone/pull the source repo
    resolved_clone = installer.clone_or_pull(resolved_clone, repo_url, branch)
    installer.set_clone_path(resolved_clone)

    # 5. Install CLI globally
    installer.install_cli(resolved_clone)

    # 6. Save config
    installer.save_install_config()

    # 7. Done
    installer.done_install()


# ── add ──────────────────────────────────────────────────────
@main.group(invoke_without_command=True)
@_scope_option
@_tool_option
@_force_option
@_dry_run_option
@click.pass_context
def add(
    ctx: click.Context,
    scope: str | None,
    tool: str | None,
    force: bool,
    dry_run: bool,
) -> None:
    """Add skills and agents to a project."""
    config, clone_path = _require_config()

    ctx.ensure_object(dict)
    ctx.obj["config"] = config
    ctx.obj["clone_path"] = clone_path
    ctx.obj["scope"] = scope
    ctx.obj["tool"] = tool
    ctx.obj["force"] = force
    ctx.obj["dry_run"] = dry_run

    # If no subcommand → install everything
    if ctx.invoked_subcommand is None:
        installer = _make_installer(config, clone_path, dry_run=dry_run, scope=scope, tool=tool)
        installer.show_summary()
        if not dry_run and not force:
            click.confirm("  Proceed?", abort=True)

        installer.install_all(clone_path, force=force)
        installer.save_install_config()
        installer.done()


def _sub_opts(ctx: click.Context, scope: str | None, force: bool, dry_run: bool) -> tuple[Installer, Path, bool]:
    """Merge group-level and subcommand-level options, return (installer, source, force)."""
    scope = scope or ctx.obj["scope"]
    tool = ctx.obj.get("tool")
    force = force or ctx.obj["force"]
    dry_run = dry_run or ctx.obj["dry_run"]

    config = ctx.obj["config"]
    clone_path = ctx.obj["clone_path"]

    installer = _make_installer(config, clone_path, dry_run=dry_run, scope=scope, tool=tool)
    return installer, clone_path, force


@add.command()
@_scope_option
@_tool_option
@_force_option
@_dry_run_option
@click.pass_context
def skills(ctx: click.Context, scope: str | None, tool: str | None, force: bool, dry_run: bool) -> None:
    """Add skills to a project."""
    ctx.obj["tool"] = tool or ctx.obj.get("tool")
    installer, source, force = _sub_opts(ctx, scope, force, dry_run)
    if installer._method == "symlink":
        installer.install_skills_symlink(source)
    else:
        installer.install_skills(force=force, source=source)


@add.command()
@_scope_option
@_tool_option
@_force_option
@_dry_run_option
@click.pass_context
def agents(ctx: click.Context, scope: str | None, tool: str | None, force: bool, dry_run: bool) -> None:
    """Add agents to a project."""
    ctx.obj["tool"] = tool or ctx.obj.get("tool")
    installer, source, force = _sub_opts(ctx, scope, force, dry_run)
    if installer._method == "symlink":
        installer.install_agents_symlink(source)
    else:
        installer.install_agents(force=force, source=source)


# ── update ───────────────────────────────────────────────────
@main.command()
@_scope_option
@_dry_run_option
def update(scope: str | None, dry_run: bool) -> None:
    """Update source (git pull) and optionally re-add to a scope."""
    config, clone_path = _require_config()
    installer = Installer(dry_run=dry_run)
    installer.set_method(config.method)
    installer.set_clone_path(clone_path)
    installer.banner()

    # Pull latest
    clone_path = installer.clone_or_pull(clone_path)
    installer.set_clone_path(clone_path)

    # Update CLI
    installer.install_cli(clone_path)

    if scope is not None:
        installer.set_scope(scope)
        installer.install_all(clone_path, force=True)
        installer.save_install_config()
        installer.done()
    else:
        installer.save_install_config()
        installer._done_banner("Source updated.")
        click.echo("  To update a project, run:")
        click.echo("    uvx dev-skills add --scope user --force")
        click.echo("    uvx dev-skills add --scope project --force")
        click.echo()


# ── uninstall ────────────────────────────────────────────────
@main.command()
@click.option("--scope", type=click.Choice(["user", "project"], case_sensitive=False), required=True, help="Scope to uninstall from.")
@_tool_option
@_dry_run_option
def uninstall(scope: str, tool: str | None, dry_run: bool) -> None:
    """Remove skills and agents from a scope."""
    config = Installer.find_install_config()

    installer = Installer(dry_run=dry_run)
    installer.banner()

    if config:
        installer.set_method(config.method)
        if config.clone_path:
            installer.set_clone_path(Path(config.clone_path))

    installer.set_scope(scope, tool or "claude")
    installer.uninstall()


# ── status ───────────────────────────────────────────────────
@main.command()
def status() -> None:
    """Show installation status."""
    Installer.status()
