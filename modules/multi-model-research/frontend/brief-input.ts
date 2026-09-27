/** Lossless admission for the existing question (12k) + scope (30k) API.
 * Count Unicode code points, matching Pydantic rather than HTML's UTF-16 limits.
 * Never truncate input or restart the research service to admit a document.
 */
export const QUESTION_LIMIT = 12_000
export const SCOPE_LIMIT = 30_000
export const BRIEF_LIMIT = QUESTION_LIMIT + SCOPE_LIMIT
export const BRIEF_FILE_BYTES = BRIEF_LIMIT * 4
export const briefLength = (text: string) => Array.from(text).length

export function validateBrief(question: string, scope: string): string | null {
  if (briefLength(question.trim()) < 5) return 'briefTooShort'
  if (briefLength(scope) > SCOPE_LIMIT) return 'briefScopeTooLong'
  const separator = briefLength(question) > QUESTION_LIMIT && scope ? 2 : 0
  if (briefLength(question) + briefLength(scope) + separator > BRIEF_LIMIT) return 'briefTooLong'
  return null
}

export function packBrief(question: string, scope: string) {
  const error = validateBrief(question, scope)
  if (error) throw new Error(error)
  const points = Array.from(question)
  if (points.length <= QUESTION_LIMIT) return {question, scope}
  const suffix = scope ? '\n\n' + scope : ''
  const minimumCut = points.length + briefLength(suffix) - SCOPE_LIMIT
  let cut = QUESTION_LIMIT
  // Prefer a paragraph boundary without overflowing the second field.
  for (let index = QUESTION_LIMIT; index >= Math.max(5, minimumCut); index--) {
    if (points[index] === '\n' && points[index + 1] === '\n') { cut = index; break }
  }
  return {question: points.slice(0, cut).join(''), scope: points.slice(cut).join('') + suffix}
}

type TextFile = {name: string; size: number; arrayBuffer: () => Promise<ArrayBuffer>}
export async function readBriefFile(file: TextFile): Promise<string> {
  if (!/\.(md|markdown|txt)$/i.test(file.name)) throw new Error('briefFileType')
  if (file.size > BRIEF_FILE_BYTES) throw new Error('briefFileTooLarge')
  const bytes = await file.arrayBuffer()
  if (bytes.byteLength > BRIEF_FILE_BYTES) throw new Error('briefFileTooLarge')
  let text: string
  try { text = new TextDecoder('utf-8', {fatal: true, ignoreBOM: true}).decode(bytes) }
  catch { throw new Error('briefFileEncoding') }
  if (text.includes('\0')) throw new Error('briefFileEncoding')
  if (!text.trim()) throw new Error('briefFileEmpty')
  return text
}
