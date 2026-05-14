#!/usr/bin/env python3
"""
vault-search.py — Fast local search for Obsidian vaults.

Usage:
  python3 vault-search.py --title "payment flow" /path/to/vault
  python3 vault-search.py --content "PENDING transaction" /path/to/vault
  python3 vault-search.py --frontmatter "canvas" /path/to/vault
  python3 vault-search.py "payment" /path/to/vault   # combined (default)

Vault path can also be set via $VAULT_FOLDER env var (last arg takes precedence).
"""

import argparse
import os
import sys
import subprocess
import shutil
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

IGNORED_DIRS = {'.obsidian', '.trash', '.git'}
MAX_CONTENT_MATCHES = 20
MAX_COMBINED_RESULTS = 15


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------

def find_notes(vault: str) -> list[str]:
    """Walk vault and return absolute paths of all .md and .canvas files."""
    results = []
    for root, dirs, files in os.walk(vault):
        # Prune ignored directories in-place
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for fname in files:
            if fname.endswith(('.md', '.canvas')):
                results.append(os.path.join(root, fname))
    return results


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def mod_date(path: str) -> str:
    try:
        ts = os.path.getmtime(path)
        return datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
    except OSError:
        return 'unknown'


def first_heading(path: str) -> str:
    """Return the first # Heading found in the file, or empty string."""
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
            for line in fh:
                stripped = line.strip()
                if stripped.startswith('# '):
                    return stripped[2:].strip()
                # Stop after frontmatter + first ~30 lines to stay fast
    except OSError:
        pass
    return ''


def read_frontmatter(path: str) -> dict:
    """Parse YAML frontmatter from a .md file. Returns {} if none found."""
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
            first_line = fh.readline()
            if first_line.strip() != '---':
                return {}
            lines = []
            for line in fh:
                if line.strip() == '---':
                    break
                lines.append(line)
        # Minimal YAML parse: key: value (no nested, no lists fully)
        fm = {}
        for line in lines:
            if ':' in line:
                key, _, val = line.partition(':')
                fm[key.strip()] = val.strip().strip('"').strip("'")
        return fm
    except OSError:
        return {}


def format_result(rank: int, vault: str, path: str, title: str, match_line: str = '') -> str:
    rel = os.path.relpath(path, vault)
    date = mod_date(path)
    lines = [f'[{rank}] {rel}']
    lines.append(f'    Title: {title or os.path.splitext(os.path.basename(path))[0]}')
    lines.append(f'    Modified: {date}')
    if match_line:
        preview = match_line.strip()[:120]
        lines.append(f'    Match: "{preview}"')
    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Mode 1: Title search
# ---------------------------------------------------------------------------

def search_title(query: str, vault: str, files: list[str] | None = None) -> list[dict]:
    """
    Fuzzy/partial title search against filenames and first # Heading.
    Returns list of dicts sorted by score descending.
    """
    if files is None:
        files = find_notes(vault)

    q = query.lower()
    results = []

    for path in files:
        basename = os.path.splitext(os.path.basename(path))[0]
        score = 0
        title = ''

        # Filename match
        bn_lower = basename.lower()
        if q == bn_lower:
            score += 20        # exact match
        elif q in bn_lower:
            score += 10        # partial match

        # First heading match
        heading = first_heading(path)
        if heading:
            h_lower = heading.lower()
            if q == h_lower:
                score += 15
            elif q in h_lower:
                score += 8
            title = heading

        if score > 0:
            results.append({
                'path': path,
                'score': score,
                'title': title or basename,
                'match_line': '',
                'source': 'title',
            })

    results.sort(key=lambda x: x['score'], reverse=True)
    return results


# ---------------------------------------------------------------------------
# Mode 2: Content search
# ---------------------------------------------------------------------------

def _rg_available() -> bool:
    return shutil.which('rg') is not None


def search_content(query: str, vault: str) -> list[dict]:
    """
    Content search using rg if available, else Python fallback.
    Returns up to MAX_CONTENT_MATCHES results.
    """
    use_rg = _rg_available()

    if use_rg:
        cmd = [
            'rg', '--fixed-strings', '-i',
            '--glob', '*.md', '--glob', '*.canvas',
            '--glob', '!.obsidian',
            '-m', '1',           # first match per file
            '-l',                # list files only first pass
            query, vault,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        matched_files = [l.strip() for l in proc.stdout.splitlines() if l.strip()]
    else:
        matched_files = _python_grep_files(query, vault)

    results = []
    for fpath in matched_files[:MAX_CONTENT_MATCHES]:
        match_line = _get_first_match(query, fpath, use_rg)
        basename = os.path.splitext(os.path.basename(fpath))[0]
        title = first_heading(fpath) or basename
        results.append({
            'path': fpath,
            'score': 5,
            'title': title,
            'match_line': match_line,
            'source': 'content',
        })

    return results


def _python_grep_files(query: str, vault: str) -> list[str]:
    """Pure-Python fallback: find files containing query string."""
    q = query.lower()
    matches = []
    for root, dirs, files in os.walk(vault):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for fname in files:
            if not fname.endswith(('.md', '.canvas')):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, 'r', encoding='utf-8', errors='ignore') as fh:
                    for line in fh:
                        if q in line.lower():
                            matches.append(fpath)
                            break
            except OSError:
                pass
    return matches


def _get_first_match(query: str, fpath: str, use_rg: bool) -> str:
    if use_rg:
        proc = subprocess.run(
            ['rg', '--fixed-strings', '-i', '-m1', '--no-heading', query, fpath],
            capture_output=True, text=True
        )
        return proc.stdout.strip()
    else:
        q = query.lower()
        try:
            with open(fpath, 'r', encoding='utf-8', errors='ignore') as fh:
                for line in fh:
                    if q in line.lower():
                        return line.strip()
        except OSError:
            pass
    return ''


# ---------------------------------------------------------------------------
# Mode 3: Frontmatter search
# ---------------------------------------------------------------------------

def search_frontmatter(query: str, vault: str) -> list[dict]:
    """
    Search frontmatter fields. Matches if key or value contains query.
    Only processes .md files (frontmatter is YAML in Markdown, not canvas).
    """
    q = query.lower()
    results = []

    for root, dirs, files in os.walk(vault):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for fname in files:
            if not fname.endswith('.md'):
                continue
            fpath = os.path.join(root, fname)
            fm = read_frontmatter(fpath)
            if not fm:
                continue
            matched_fields = []
            for key, val in fm.items():
                if q in key.lower() or q in val.lower():
                    matched_fields.append(f'{key}: {val}')
            if matched_fields:
                basename = os.path.splitext(fname)[0]
                title = first_heading(fpath) or basename
                results.append({
                    'path': fpath,
                    'score': 10 * len(matched_fields),
                    'title': title,
                    'match_line': ' | '.join(matched_fields),
                    'source': 'frontmatter',
                })

    results.sort(key=lambda x: x['score'], reverse=True)
    return results


# ---------------------------------------------------------------------------
# Mode 4: Combined (default)
# ---------------------------------------------------------------------------

def search_combined(query: str, vault: str) -> list[dict]:
    """
    Run title + content search in parallel, deduplicate, rank.
    Title matches come first; content matches follow.
    """
    files = find_notes(vault)

    with ThreadPoolExecutor(max_workers=2) as executor:
        fut_title = executor.submit(search_title, query, vault, files)
        fut_content = executor.submit(search_content, query, vault)
        title_results = fut_title.result()
        content_results = fut_content.result()

    # Deduplicate: title matches take priority
    seen = {}
    for r in title_results:
        seen[r['path']] = r

    for r in content_results:
        if r['path'] not in seen:
            seen[r['path']] = r
        else:
            # Merge: keep title entry but add match_line from content if missing
            existing = seen[r['path']]
            if not existing['match_line'] and r['match_line']:
                existing['match_line'] = r['match_line']

    combined = list(seen.values())
    # Title matches (source='title') first, then content, then by score desc
    combined.sort(key=lambda x: (0 if x['source'] == 'title' else 1, -x['score']))
    return combined[:MAX_COMBINED_RESULTS]


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def print_results(results: list[dict], vault: str, query: str, mode: str) -> None:
    if not results:
        print(f'No results found for: {query!r}')
        return

    print(f'Search results for {query!r} [{mode}] — {len(results)} match(es):\n')
    for i, r in enumerate(results, 1):
        print(format_result(i, vault, r['path'], r['title'], r.get('match_line', '')))
        print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def resolve_vault(args_vault: str | None) -> str:
    vault = args_vault or os.environ.get('VAULT_FOLDER', '')
    if not vault:
        print(
            'Error: vault path required. Pass it as the last argument or set $VAULT_FOLDER.',
            file=sys.stderr
        )
        print_usage()
        sys.exit(1)
    vault = os.path.expanduser(vault)
    if not os.path.isdir(vault):
        print(f'Error: vault path does not exist or is not a directory: {vault}', file=sys.stderr)
        sys.exit(1)
    return vault


def print_usage() -> None:
    print(__doc__)


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Fast local Obsidian vault search.',
        add_help=True,
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--title', metavar='QUERY', help='Search by title / first heading')
    group.add_argument('--content', metavar='QUERY', help='Search file contents (uses rg if available)')
    group.add_argument('--frontmatter', metavar='QUERY', help='Search YAML frontmatter fields')

    parser.add_argument('query', nargs='?', help='Query for combined search (default mode)')
    parser.add_argument('vault', nargs='?', help='Path to vault (or set $VAULT_FOLDER)')

    args = parser.parse_args()

    # Determine vault and query
    # Positional args: if two positional args → (query, vault); if one → ambiguous, try vault first
    vault_path = resolve_vault(args.vault)

    if args.title:
        results = search_title(args.title, vault_path)
        print_results(results, vault_path, args.title, 'title')
    elif args.content:
        results = search_content(args.content, vault_path)
        print_results(results, vault_path, args.content, 'content')
    elif args.frontmatter:
        results = search_frontmatter(args.frontmatter, vault_path)
        print_results(results, vault_path, args.frontmatter, 'frontmatter')
    elif args.query:
        results = search_combined(args.query, vault_path)
        print_results(results, vault_path, args.query, 'combined')
    else:
        print('Error: a query is required.', file=sys.stderr)
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
