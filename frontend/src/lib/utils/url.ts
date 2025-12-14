/**
 * Utility functions for URL-friendly ID encoding/decoding
 * 
 * SurrealDB IDs have format "table:id" (e.g., "notebook:wh9g0w2ssysrrby2dg9f")
 * We strip the table prefix for cleaner URLs
 */

/**
 * Convert a SurrealDB ID to a URL-friendly format
 * @param id - Full SurrealDB ID (e.g., "notebook:wh9g0w2ssysrrby2dg9f")
 * @returns URL-friendly ID (e.g., "wh9g0w2ssysrrby2dg9f")
 */
export function toUrlId(id: string): string {
  // Strip the table prefix if it exists
  const colonIndex = id.indexOf(':')
  return colonIndex >= 0 ? id.substring(colonIndex + 1) : id
}

/**
 * Convert a URL-friendly ID back to a full SurrealDB ID
 * @param urlId - URL-friendly ID (e.g., "wh9g0w2ssysrrby2dg9f")
 * @param table - Table name (e.g., "notebook")
 * @returns Full SurrealDB ID (e.g., "notebook:wh9g0w2ssysrrby2dg9f")
 */
export function fromUrlId(urlId: string, table: string): string {
  // If already has a colon, return as-is (backwards compatibility)
  if (urlId.includes(':')) {
    return urlId
  }
  return `${table}:${urlId}`
}

/**
 * Encode a SurrealDB ID for use in URLs
 * This strips the table prefix and returns the clean ID
 * 
 * @example
 * encodeNotebookId("notebook:abc123") // "abc123"
 */
export function encodeNotebookId(id: string): string {
  return toUrlId(id)
}

/**
 * Decode a URL ID back to a full notebook ID
 * Handles both old (with notebook:) and new (without) formats
 * 
 * @example
 * decodeNotebookId("abc123") // "notebook:abc123"
 * decodeNotebookId("notebook:abc123") // "notebook:abc123"
 * decodeNotebookId("notebook%3Aabc123") // "notebook:abc123"
 */
export function decodeNotebookId(urlId: string): string {
  // First decode any URL encoding (backwards compatibility)
  const decoded = decodeURIComponent(urlId)
  return fromUrlId(decoded, 'notebook')
}

/**
 * Encode a source ID for URLs
 */
export function encodeSourceId(id: string): string {
  return toUrlId(id)
}

/**
 * Decode a source ID from URLs
 */
export function decodeSourceId(urlId: string): string {
  const decoded = decodeURIComponent(urlId)
  return fromUrlId(decoded, 'source')
}
