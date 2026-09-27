import { unzipSync } from 'fflate'
import { BRIEF_LIMIT, briefLength, readBriefFile } from './brief-input'

export const DOCUMENT_EXTENSIONS = ['md', 'markdown', 'txt', 'csv', 'json', 'yaml', 'yml', 'pdf', 'docx']
export const DOCUMENT_ACCEPT = DOCUMENT_EXTENSIONS.map(value => '.' + value).join(',')
export const DOCUMENT_COUNT = 10
export const DOCUMENT_BYTES = 8 * 1024 * 1024
export const DOCUMENT_TOTAL_BYTES = 32 * 1024 * 1024
const BLOCKED = /\.(exe|dll|com|bat|cmd|ps1|sh|bash|zsh|app|dmg|pkg|msi|js|mjs|cjs|vbs|scr|jar|zip|rar|7z|docm|xlsm|pptm)(\.|$)/i
export type BriefDocument = {id: string; name: string; size: number; text: string; sha256: string; kind: string; error?: string}

export function documentKind(name: string): string {
  if (/[\\/\r\n\0]/.test(name) || BLOCKED.test(name)) throw new Error('briefFileBlocked')
  const kind = name.split('.').pop()?.toLowerCase() || ''
  if (!DOCUMENT_EXTENSIONS.includes(kind)) throw new Error('briefFileType')
  return kind
}

export function composeBrief(question: string, files: BriefDocument[]): string {
  const parts = question ? [question] : []
  for (const file of files) {
    if (file.error) throw new Error('briefFilesNeedAttention')
    parts.push('## Document: ' + file.name + '\nSHA-256: ' + file.sha256 + '\n\n' + file.text)
  }
  return parts.join('\n\n')
}

function xml(data: Uint8Array): Document {
  const text = new TextDecoder('utf-8', {fatal: true}).decode(data)
  if (/<!DOCTYPE|<!ENTITY/i.test(text)) throw new Error('briefFileBlocked')
  const doc = new DOMParser().parseFromString(text, 'application/xml')
  if (doc.getElementsByTagName('parsererror').length) throw new Error('briefFileReadError')
  return doc
}

/** Check central-directory bounds before asking the ZIP reader to inflate any XML. */
export function checkDocxArchive(bytes: Uint8Array) {
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength)
  let end = -1
  for (let i = bytes.length - 22; i >= Math.max(0, bytes.length - 65557); i--) {
    if (view.getUint32(i, true) === 0x06054b50 && i + 22 + view.getUint16(i + 20, true) === bytes.length) { end = i; break }
  }
  if (end < 0) throw new Error('briefFileSignature')
  const count = view.getUint16(end + 10, true), size = view.getUint32(end + 12, true)
  let pos = view.getUint32(end + 16, true), total = 0
  if (count > 2000 || view.getUint32(end + 4, true) !== 0 || pos + size !== end) throw new Error('briefArchiveTooLarge')
  const names = new Set<string>()
  for (let i = 0; i < count; i++) {
    if (pos + 46 > end || view.getUint32(pos, true) !== 0x02014b50) throw new Error('briefFileSignature')
    const flags = view.getUint16(pos + 8, true), expanded = view.getUint32(pos + 24, true)
    const nameLength = view.getUint16(pos + 28, true), extra = view.getUint16(pos + 30, true), comment = view.getUint16(pos + 32, true)
    if (pos + 46 + nameLength + extra + comment > end) throw new Error('briefFileSignature')
    const name = new TextDecoder('utf-8', {fatal: true}).decode(bytes.subarray(pos + 46, pos + 46 + nameLength))
    total += expanded
    if (total > 40 * 1024 * 1024 || expanded > 8 * 1024 * 1024 || flags & 1) throw new Error('briefArchiveTooLarge')
    if (names.has(name) || /(^\/|\.\.|\\|vbaProject|activeX|embeddings\/)/i.test(name)) throw new Error('briefFileBlocked')
    names.add(name); pos += 46 + nameLength + extra + comment
  }
  if (pos !== end || !names.has('[Content_Types].xml') || !names.has('word/document.xml')) throw new Error('briefFileSignature')
}

export function extractDocx(bytes: Uint8Array): string {
  checkDocxArchive(bytes)
  const parts = unzipSync(bytes, {filter: file => /^word\/(document|header\d+|footer\d+|footnotes|endnotes|comments)\.xml$/.test(file.name) || /^word\/_rels\/[^/]+\.rels$/.test(file.name)})
  const output: string[] = []
  const names = Object.keys(parts).sort((a,b) => a === 'word/document.xml' ? -1 : b === 'word/document.xml' ? 1 : a.localeCompare(b))
  for (const name of names) {
    const doc = xml(parts[name])
    if (name.endsWith('.rels')) {
      for (const node of Array.from(doc.getElementsByTagName('Relationship'))) {
        if (node.getAttribute('Type')?.endsWith('/hyperlink')) output.push(node.getAttribute('Target') || '')
      }
    } else {
      for (const paragraph of Array.from(doc.getElementsByTagNameNS('*', 'p'))) {
        const words: string[] = []
        for (const node of Array.from(paragraph.getElementsByTagNameNS('*', '*'))) {
          if (node.localName === 't') words.push(node.textContent || '')
          else if (node.localName === 'tab') words.push('\t')
          else if (node.localName === 'br') words.push('\n')
        }
        output.push(words.join(''))
      }
    }
  }
  return output.join('\n\n')
}

async function extractPdf(bytes: Uint8Array): Promise<string> {
  if (new TextDecoder().decode(bytes.subarray(0,5)) !== '%PDF-') throw new Error('briefFileSignature')
  const pdfjs = await import('pdfjs-dist')
  pdfjs.GlobalWorkerOptions.workerSrc = new URL('pdfjs-dist/build/pdf.worker.min.mjs', import.meta.url).toString()
  const task = pdfjs.getDocument({data:bytes, disableFontFace:true, useWorkerFetch:false, stopAtErrors:true})
  let timer: ReturnType<typeof setTimeout> | undefined
  try {
    return await Promise.race([
      (async()=>{
        const document = await task.promise
        if (document.numPages > 250) throw new Error('briefPdfPages')
        const parts: string[] = []; let length = 0
        for (let n = 1; n <= document.numPages; n++) {
          const page = await document.getPage(n), content = await page.getTextContent()
          const text = content.items.map(item => 'str' in item ? item.str + (item.hasEOL ? '\n' : ' ') : '').join('')
          if (!text.trim()) throw new Error('briefScannedPdf')
          const links = (await page.getAnnotations()).flatMap(annotation => typeof annotation.url === 'string' ? [annotation.url] : [])
          const passage = text + (links.length ? '\n\n' + [...new Set(links)].join('\n') : '')
          parts.push(passage); length += briefLength(passage) + 2
          if (length > BRIEF_LIMIT) throw new Error('briefTooLong')
          page.cleanup()
        }
        return parts.join('\n\n')
      })(),
      new Promise<never>((_,reject)=>{timer=setTimeout(()=>reject(new Error('briefFileTimeout')),30_000)})
    ])
  } catch (err) {
    if (err instanceof Error && err.name === 'PasswordException') throw new Error('briefPdfPassword')
    throw err
  } finally { if(timer)clearTimeout(timer); await task.destroy() }
}

export async function readDocument(file: File): Promise<BriefDocument> {
  const kind = documentKind(file.name)
  if (file.size > DOCUMENT_BYTES) throw new Error('briefFileTooLarge')
  const buffer = await file.arrayBuffer(), bytes = new Uint8Array(buffer)
  if (bytes.byteLength > DOCUMENT_BYTES) throw new Error('briefFileTooLarge')
  const hash = await crypto.subtle.digest('SHA-256',buffer)
  const sha256 = Array.from(new Uint8Array(hash), value=>value.toString(16).padStart(2,'0')).join('')
  let text: string
  if (kind === 'pdf') text = await extractPdf(bytes)
  else if (kind === 'docx') text = extractDocx(bytes)
  else {
    // Extension alone is not a type check: renamed binaries/archives are rejected too.
    if (bytes[0]===0x4d&&bytes[1]===0x5a || bytes[0]===0x50&&bytes[1]===0x4b || bytes[0]===0x7f&&bytes[1]===0x45 || new TextDecoder().decode(bytes.subarray(0,5))==='%PDF-') throw new Error('briefFileSignature')
    text = await readBriefFile({name:'document.txt',size:bytes.byteLength,arrayBuffer:async()=>buffer})
  }
  if (!text.trim()) throw new Error('briefFileEmpty')
  if (briefLength(text)>BRIEF_LIMIT) throw new Error('briefTooLong')
  return {id:crypto.randomUUID(), name:file.name, size:file.size, kind, text, sha256}
}
