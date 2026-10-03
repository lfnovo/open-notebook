"""Native artifact generation pipeline (#203 artifacts tab, stage 1).

Pure pipeline logic, split so every external dependency sits behind one small
seam:

- ``outline``: plan the document (one LLM call) and the shared LLM bridge
- ``composition``: per-section retrieval, grounded writing, citations
- ``diagrams``: ```mermaid``` fences -> 2x PNG (mermaidx, no Node/browser)
- ``render``: Markdown -> pptx/docx/html via pandoc + the reference deck

The pipeline is driven by the ``generate_artifact`` command (stage 2) and
persists a ``GeneratedArtifact`` row (``open_notebook.domain.artifact``).
"""
