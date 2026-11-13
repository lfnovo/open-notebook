/**
 * Plain-text preview of a markdown string, for compact cards that show the
 * first few lines of a model's output (e.g. a source insight).
 *
 * Insights are written in markdown (headings, bold, lists, tables), so slicing
 * the raw string shows `##`, `**` and `*` markers. This strips the common
 * markers, collapses whitespace and truncates with an ellipsis. It is a
 * preview helper, not a markdown parser: the full text is always rendered
 * with the real markdown renderer in the detail dialog.
 */
export function markdownPreview(markdown: string, maxLength = 180): string {
  const text = markdown
    // Fenced code blocks carry no readable preview text
    .replace(/```[\s\S]*?```/g, ' ')
    // Images keep their alt text, links keep their label
    .replace(/!\[([^\]]*)\]\([^)]*\)/g, '$1')
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
    // Block markers at the start of a line
    .replace(/^\s{0,3}#{1,6}\s+/gm, '')
    .replace(/^\s{0,3}>\s?/gm, '')
    .replace(/^\s*(?:[-*+]|\d+[.)])\s+/gm, '')
    // Horizontal rules and table separator rows
    .replace(/^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)*\|?\s*$/gm, ' ')
    // Table cell borders
    .replace(/\|/g, ' ')
    // Inline emphasis; underscores only count at word edges so snake_case survives
    .replace(/\*\*(.+?)\*\*/g, '$1')
    .replace(/(^|[^\w])__(.+?)__(?=[^\w]|$)/g, '$1$2')
    .replace(/\*(.+?)\*/g, '$1')
    .replace(/(^|[^\w])_(.+?)_(?=[^\w]|$)/g, '$1$2')
    .replace(/~~(.+?)~~/g, '$1')
    .replace(/`([^`]*)`/g, '$1')
    .replace(/\s+/g, ' ')
    .trim()

  if (text.length <= maxLength) return text
  return `${text.slice(0, maxLength).trimEnd()}…`
}
