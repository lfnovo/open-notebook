"""Safe, read-only access to local code repositories for the repo-review feature.

Three responsibilities:
  - validate_repo_path(): enforce the REPO_REVIEW_ALLOWED_ROOTS security boundary
  - build_file_tree(): a capped, noise-filtered listing of the repo's files
  - grep_repo(): pattern search over the repo (ripgrep when available, Python fallback)

Everything here is read-only. Nothing writes to or executes code from the repo.
"""

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from loguru import logger

from open_notebook.config import REPO_REVIEW_ALLOWED_ROOTS
from open_notebook.exceptions import ConfigurationError, InvalidInputError

# Directories that never carry useful signal for a best-practices review.
IGNORED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
    ".next",
    ".turbo",
    "target",
    "out",
    "coverage",
    ".idea",
    ".vscode",
}

# Extensions we skip when reading content (binaries, media, lockfiles-as-noise).
BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".svg", ".pdf",
    ".zip", ".gz", ".tar", ".tgz", ".rar", ".7z", ".jar", ".war",
    ".mp3", ".mp4", ".mov", ".avi", ".wav", ".flac", ".ogg",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".so", ".dylib", ".dll", ".exe", ".bin", ".o", ".a", ".class", ".pyc",
    ".lock", ".db", ".sqlite", ".sqlite3",
}

# Hard caps so a huge monorepo can never blow up memory or context.
MAX_TREE_FILES = 4000
MAX_FILE_SIZE_BYTES = 1_000_000  # skip files larger than ~1MB
MAX_GREP_HITS = 400
MAX_HITS_PER_FILE = 20
CONTEXT_LINES = 2


@dataclass
class GrepHit:
    """A single pattern match with surrounding context."""

    file: str  # repo-relative path
    line: int  # 1-based line number of the match
    snippet: str  # the matched line plus a couple of context lines


def validate_repo_path(path: str) -> Path:
    """Resolve and authorize a repo path against the allowed-roots allowlist.

    Raises ConfigurationError if the feature isn't configured, InvalidInputError
    if the path is missing, not a directory, or escapes the allowed roots.
    Returns the resolved absolute Path on success.
    """
    if not path or not path.strip():
        raise InvalidInputError("Repository path must be provided")

    if not REPO_REVIEW_ALLOWED_ROOTS:
        raise ConfigurationError(
            "Repo review is not configured. Set REPO_REVIEW_ALLOWED_ROOTS to one or "
            "more absolute directories the backend is allowed to scan."
        )

    # resolve() collapses '..' and follows symlinks, so an escape attempt lands on
    # its real target — which then fails the is_relative_to check below.
    resolved = Path(path).expanduser().resolve()

    allowed_roots = [Path(root).expanduser().resolve() for root in REPO_REVIEW_ALLOWED_ROOTS]
    if not any(_is_within(resolved, root) for root in allowed_roots):
        raise InvalidInputError(
            f"Path '{path}' is outside the allowed roots. Allowed: "
            f"{', '.join(str(r) for r in allowed_roots)}"
        )

    if not resolved.exists():
        raise InvalidInputError(f"Path does not exist: {resolved}")
    if not resolved.is_dir():
        raise InvalidInputError(f"Path is not a directory: {resolved}")

    return resolved


def _is_within(child: Path, parent: Path) -> bool:
    """True if child is parent or lives inside it (both already resolved)."""
    try:
        return child == parent or parent in child.parents
    except Exception:
        return False


def _iter_files(root: Path):
    """Yield reviewable files under root, pruning ignored dirs and binaries."""
    count = 0
    for dirpath, dirnames, filenames in os.walk(root):
        # Prune ignored directories in place so os.walk skips them entirely.
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS and not d.startswith(".")]
        for name in filenames:
            if name.startswith("."):
                continue
            fpath = Path(dirpath) / name
            if fpath.suffix.lower() in BINARY_EXTENSIONS:
                continue
            try:
                if fpath.stat().st_size > MAX_FILE_SIZE_BYTES:
                    continue
            except OSError:
                continue
            yield fpath
            count += 1
            if count >= MAX_TREE_FILES:
                logger.warning(
                    f"repo_scan: file tree truncated at {MAX_TREE_FILES} files for {root}"
                )
                return


def build_file_tree(root: Path) -> List[str]:
    """Return a capped list of repo-relative file paths, for orienting the LLM."""
    return [str(f.relative_to(root)) for f in _iter_files(root)]


def grep_repo(root: Path, patterns: List[str]) -> List[GrepHit]:
    """Search the repo for any of the given regex patterns.

    Uses ripgrep when available (fast, respects .gitignore), falling back to a
    pure-Python walk. Results are capped globally and per-file.
    """
    patterns = [p for p in (patterns or []) if p and p.strip()]
    if not patterns:
        return []

    if shutil.which("rg"):
        try:
            return _grep_with_ripgrep(root, patterns)
        except Exception as e:
            logger.warning(f"repo_scan: ripgrep failed ({e}); falling back to Python scan")
    return _grep_with_python(root, patterns)


def _grep_with_ripgrep(root: Path, patterns: List[str]) -> List[GrepHit]:
    cmd = [
        "rg",
        "--no-heading",
        "--line-number",
        "--with-filename",
        "--color", "never",
        "--max-columns", "400",
        f"--max-count={MAX_HITS_PER_FILE}",
        "-C", str(CONTEXT_LINES),
        "--ignore-case",
    ]
    for d in IGNORED_DIRS:
        cmd += ["--glob", f"!**/{d}/**"]
    for p in patterns:
        cmd += ["-e", p]
    cmd.append(str(root))

    proc = subprocess.run(
        cmd, capture_output=True, text=True, timeout=120, check=False
    )
    # rg exits 1 when there are no matches — that's not an error for us.
    if proc.returncode not in (0, 1):
        raise RuntimeError(proc.stderr.strip() or f"rg exited {proc.returncode}")

    hits: List[GrepHit] = []
    # With -C, rg groups match/context lines and separates blocks with '--'.
    block: List[str] = []
    for raw in proc.stdout.splitlines():
        if raw == "--":
            _absorb_rg_block(root, block, hits)
            block = []
            if len(hits) >= MAX_GREP_HITS:
                break
        else:
            block.append(raw)
    if block and len(hits) < MAX_GREP_HITS:
        _absorb_rg_block(root, block, hits)
    return hits[:MAX_GREP_HITS]


def _absorb_rg_block(root: Path, block: List[str], hits: List[GrepHit]) -> None:
    """Turn one ripgrep -C block into a GrepHit anchored on its matched line.

    Matched lines use 'file:line:text'; context lines use 'file-line-text'. We
    anchor on the first match line and attach the whole block as the snippet.
    """
    match_file: Optional[str] = None
    match_line: Optional[int] = None
    snippet_lines: List[str] = []
    for entry in block:
        parsed = _parse_rg_line(entry)
        if parsed is None:
            continue
        fpath, lineno, text, is_match = parsed
        snippet_lines.append(text)
        if is_match and match_line is None:
            try:
                match_file = str(Path(fpath).resolve().relative_to(root))
            except Exception:
                match_file = fpath
            match_line = lineno
    if match_file is not None and match_line is not None:
        hits.append(
            GrepHit(file=match_file, line=match_line, snippet="\n".join(snippet_lines).strip())
        )


def _parse_rg_line(entry: str):
    """Parse an rg output line into (file, line, text, is_match) or None.

    Match lines: 'path:123:content'. Context lines: 'path-123-content'.
    Windows-style drive letters are not handled (POSIX deployment assumed).
    """
    for sep, is_match in ((":", True), ("-", False)):
        # path can contain ':' on its own, so split from the right around the
        # 'sep<digits>sep' line-number marker using a regex.
        m = re.match(rf"^(.*?){re.escape(sep)}(\d+){re.escape(sep)}(.*)$", entry)
        if m:
            return m.group(1), int(m.group(2)), m.group(3), is_match
    return None


def _grep_with_python(root: Path, patterns: List[str]) -> List[GrepHit]:
    try:
        regexes = [re.compile(p, re.IGNORECASE) for p in patterns]
    except re.error as e:
        logger.warning(f"repo_scan: invalid probe pattern ({e}); skipping bad patterns")
        regexes = []
        for p in patterns:
            try:
                regexes.append(re.compile(p, re.IGNORECASE))
            except re.error:
                continue
    if not regexes:
        return []

    hits: List[GrepHit] = []
    for fpath in _iter_files(root):
        try:
            text = fpath.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        lines = text.splitlines()
        file_hits = 0
        for i, line in enumerate(lines):
            if any(rx.search(line) for rx in regexes):
                start = max(0, i - CONTEXT_LINES)
                end = min(len(lines), i + CONTEXT_LINES + 1)
                snippet = "\n".join(lines[start:end]).strip()
                hits.append(
                    GrepHit(file=str(fpath.relative_to(root)), line=i + 1, snippet=snippet)
                )
                file_hits += 1
                if file_hits >= MAX_HITS_PER_FILE or len(hits) >= MAX_GREP_HITS:
                    break
        if len(hits) >= MAX_GREP_HITS:
            break
    return hits[:MAX_GREP_HITS]
