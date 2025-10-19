#!/usr/bin/env python3
"""
Export documentation by consolidating markdown files from each docs folder.

This script:
1. Scans all subdirectories in the docs/ folder
2. For each subdirectory, concatenates all .md files (except index.md)
3. Saves the consolidated content to doc_exports/{folder_name}.md
"""

import logging
from pathlib import Path
from typing import List

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def get_markdown_files(folder: Path) -> List[Path]:
    """Get all markdown files in a folder, excluding index.md files."""
    md_files = [f for f in folder.glob("*.md") if f.name.lower() != "index.md"]
    return sorted(md_files)  # Sort for consistent ordering


def consolidate_folder(folder: Path, output_dir: Path) -> None:
    """Consolidate all markdown files from a folder into a single file."""
    md_files = get_markdown_files(folder)

    if not md_files:
        logger.info(f"  Skipping {folder.name} - no markdown files found")
        return

    output_file = output_dir / f"{folder.name}.md"

    with output_file.open("w", encoding="utf-8") as outf:
        # Write header
        outf.write(f"# {folder.name.replace('-', ' ').title()}\n\n")
        outf.write(f"This document consolidates all content from the {folder.name} documentation folder.\n\n")
        outf.write("---\n\n")

        # Process each markdown file
        for md_file in md_files:
            logger.info(f"  Adding {md_file.name}")

            # Add section header with filename
            outf.write(f"## {md_file.stem.replace('-', ' ').title()}\n\n")
            outf.write(f"*Source: {md_file.name}*\n\n")

            # Add file content
            content = md_file.read_text(encoding="utf-8")
            outf.write(content)
            outf.write("\n\n---\n\n")

    logger.info(f"  ✓ Created {output_file.name} ({len(md_files)} files)")


def main():
    """Main function to export documentation."""
    # Define paths
    docs_dir = Path("docs")
    output_dir = Path("doc_exports")

    # Validate docs directory exists
    if not docs_dir.exists():
        logger.error(f"Documentation directory '{docs_dir}' not found")
        return

    # Create output directory
    output_dir.mkdir(exist_ok=True)
    logger.info(f"Output directory: {output_dir.absolute()}")

    # Get all subdirectories in docs/
    subdirs = [d for d in docs_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]

    if not subdirs:
        logger.warning("No subdirectories found in docs/")
        return

    logger.info(f"Found {len(subdirs)} documentation folders\n")

    # Process each subdirectory
    for subdir in sorted(subdirs):
        logger.info(f"Processing {subdir.name}...")
        consolidate_folder(subdir, output_dir)

    logger.info(f"\n✓ Documentation export complete!")
    logger.info(f"Exported files are in: {output_dir.absolute()}")


if __name__ == "__main__":
    main()
