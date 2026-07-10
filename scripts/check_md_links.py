#!/usr/bin/env python3
"""Check that relative markdown links point to files that exist.

Scans every tracked *.md file in the repo and validates relative link targets
(external URLs, anchors and mailto links are skipped; code blocks and inline
code spans are ignored). Exits 1 if any broken link is found.

Run locally:  python3 scripts/check_md_links.py
"""

import os
import re
import subprocess
import sys

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
SKIP_PREFIXES = ("http://", "https://", "mailto:", "#", "<")


def repo_root() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"], text=True
    ).strip()


def tracked_markdown_files(root: str) -> list[str]:
    out = subprocess.check_output(["git", "ls-files", "*.md"], text=True, cwd=root)
    return [line for line in out.splitlines() if line]


def main() -> int:
    root = repo_root()
    broken: list[str] = []

    for rel in tracked_markdown_files(root):
        path = os.path.join(root, rel)
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            continue

        text = FENCED_CODE_RE.sub("", text)
        text = INLINE_CODE_RE.sub("", text)

        for match in LINK_RE.finditer(text):
            target = match.group(1)
            if target.startswith(SKIP_PREFIXES):
                continue
            file_part = target.split("#")[0]
            if not file_part:
                continue
            if file_part.startswith("/"):
                resolved = os.path.join(root, file_part.lstrip("/"))
            else:
                resolved = os.path.normpath(
                    os.path.join(os.path.dirname(path), file_part)
                )
            if not os.path.exists(resolved):
                broken.append(f"{rel}: {target}")

    if broken:
        print(f"{len(broken)} broken relative link(s):")
        for entry in broken:
            print(f"  {entry}")
        return 1

    print("All relative markdown links resolve.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
