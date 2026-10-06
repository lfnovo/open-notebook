import { PROXY_MAX_UPLOAD_BYTES } from './upload-limits'

// The proxy limit applies to the whole request body, so leave room for the
// multipart boundaries and the other form fields sent along with the file.
const MULTIPART_HEADROOM_BYTES = 1024 * 1024

export const PROXY_UPLOAD_DOCS_URL =
  'https://github.com/lfnovo/open-notebook/blob/main/docs/5-CONFIGURATION/reverse-proxy.md#upload-size-413-errors'

/**
 * True when API requests go through the frontend's own /api/* rewrite:
 * an empty or relative API URL, or one on the same origin as the page.
 */
export function uploadsUseFrontendProxy(apiUrl: string, pageOrigin: string): boolean {
  if (!apiUrl) return true
  try {
    return new URL(apiUrl, pageOrigin).origin === pageOrigin
  } catch {
    return false
  }
}

/**
 * Files the rewrite would cut off. Empty when the API is called directly:
 * there the API's own limit (OPEN_NOTEBOOK_MAX_UPLOAD_SIZE_MB) answers with a 413.
 */
export function filesTooLargeForProxy(files: File[], apiUrl: string, pageOrigin: string): File[] {
  if (!uploadsUseFrontendProxy(apiUrl, pageOrigin)) return []
  return files.filter((file) => file.size > PROXY_MAX_UPLOAD_BYTES - MULTIPART_HEADROOM_BYTES)
}
