/**
 * Strip Markdown formatting down to plain text, for use in short UI previews
 * (e.g. insight card previews) where raw `##`, `**`, `*` or table `|` markers
 * would otherwise leak into the visible text.
 *
 * No dependencies — plain regex passes only. Not a full Markdown parser:
 * it is intentionally conservative and never drops the text content itself.
 */

/** Remove Markdown syntax, keeping the readable text. */
export function stripMarkdown(markdown: string): string {
  let text = markdown

  // Fenced code blocks: keep the inner content, drop the fences (and language tag)
  text = text.replace(/```[a-zA-Z0-9+-]*\n?([\s\S]*?)```/g, '$1')
  // Inline code: `code` -> code
  text = text.replace(/`([^`]+)`/g, '$1')
  // Images: ![alt](url) -> alt
  text = text.replace(/!\[([^\]]*)\]\([^)]*\)/g, '$1')
  // Links: [text](url) -> text
  text = text.replace(/\[([^\]]*)\]\([^)]*\)/g, '$1')
  // ATX headings: ## Title -> Title (line-start or after whitespace;
  // #hashtag and C# are left alone)
  text = text.replace(/(^|\s)#{1,6}(?=\s|$)/gm, '$1')
  // Setext heading underlines are caught by the hr rule below
  // Bold / italic with asterisks: **text** -> text, *text* -> text
  // (paired only, so "2 * 3 = 6" is left alone)
  text = text.replace(/\*\*([^*]+)\*\*/g, '$1')
  text = text.replace(/\*([^*]+)\*/g, '$1')
  // Bold with underscores: __text__ -> text
  text = text.replace(/__([^_]+)__/g, '$1')
  // Italic with underscores: _text_ -> text (word-bounded, so snake_case survives)
  text = text.replace(/\b_([^_\s][^_]*?)_\b/g, '$1')
  // Strikethrough: ~~text~~ -> text
  text = text.replace(/~~([^~]+)~~/g, '$1')
  // Blockquotes: > quote -> quote
  text = text.replace(/^>\s?/gm, '')
  // Unordered list markers: - item / * item / + item -> item
  text = text.replace(/^\s*[-*+]\s+/gm, '')
  // Ordered list markers: 1. item / 1) item -> item
  text = text.replace(/^\s*\d+[.)]\s+/gm, '')
  // Table separator rows: | --- | --- | -> (removed entirely)
  text = text.replace(/^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?\s*$/gm, '')
  // Tables: drop the pipes (cell content is kept)
  text = text.replace(/\|/g, ' ')
  // Horizontal rules: --- / *** / ___ on their own line
  text = text.replace(/^\s*([-*_])\1{2,}\s*$/gm, '')
  // HTML tags
  text = text.replace(/<[^>]+>/g, '')
  // Escaped punctuation: \* -> *
  text = text.replace(/\\([\\`*_{}[\]()#+\-.!])/g, '$1')
  // Collapse all whitespace (incl. newlines) to single spaces
  text = text.replace(/\s+/g, ' ').trim()

  return text
}

/**
 * Build a plain-text preview of Markdown content, truncated to `maxLength`
 * characters with an ellipsis appended when truncated.
 */
export function markdownPreview(content: string, maxLength = 180): string {
  const plain = stripMarkdown(content)
  return plain.length > maxLength ? `${plain.slice(0, maxLength)}…` : plain
}
