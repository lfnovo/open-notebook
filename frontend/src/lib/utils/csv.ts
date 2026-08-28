/**
 * Escapes a single CSV field per RFC 4180: wraps it in double quotes if it
 * contains a comma, a double quote, or a newline, doubling any internal
 * double quotes.
 */
export function toCsvField(value: string): string {
  if (/[",\n\r]/.test(value)) {
    return `"${value.replace(/"/g, '""')}"`
  }
  return value
}

export function rowsToCsv(rows: string[][]): string {
  return rows.map((row) => row.map(toCsvField).join(',')).join('\r\n')
}

/** Triggers a browser download of `content` as a file, via a Blob + temporary <a download> link. */
export function downloadTextFile(content: string, filename: string, mimeType = 'text/csv;charset=utf-8;') {
  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}
