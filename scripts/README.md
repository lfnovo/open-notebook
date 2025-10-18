# Scripts Documentation

## export_docs.py

Consolidates markdown documentation files for use with ChatGPT or other platforms with file upload limits.

### What It Does

- Scans all subdirectories in the `docs/` folder
- For each subdirectory, combines all `.md` files (excluding `index.md` files)
- Creates one consolidated markdown file per subdirectory
- Saves all exported files to `doc_exports/` in the project root

### Usage

```bash
# Using Makefile (recommended)
make export-docs

# Or run directly with uv
uv run python scripts/export_docs.py

# Or run with standard Python
python scripts/export_docs.py
```

### Output

The script creates `doc_exports/` directory with consolidated files like:

- `getting-started.md` - All getting-started documentation
- `user-guide.md` - All user guide content
- `features.md` - All feature documentation
- `development.md` - All development documentation
- etc.

Each exported file includes:
- A main header with the folder name
- Section headers for each source file
- Source file attribution
- The complete content from each markdown file
- Visual separators between sections

### Example Output Structure

```markdown
# Getting Started

This document consolidates all content from the getting-started documentation folder.

---

## Installation

*Source: installation.md*

[Full content of installation.md]

---

## Quick Start

*Source: quick-start.md*

[Full content of quick-start.md]

---
```

### Notes

- The `doc_exports/` directory is gitignored and safe to regenerate anytime
- Index files (`index.md`) are automatically excluded
- Files are sorted alphabetically for consistent output
- The script handles subdirectories only (ignores files in the root `docs/` folder)
