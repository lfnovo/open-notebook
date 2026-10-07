import { PROXY_MAX_UPLOAD_BYTES } from './upload-limits'

// The proxy limit applies to the whole request body, so leave room for the
// multipart boundaries and the other form fields sent along with the file.
const MULTIPART_HEADROOM_BYTES = 1024 * 1024

// Served by the frontend itself (src/app/api/frontend-proxy/route.ts). Next.js
// route handlers win over the /api/* rewrite, so this answers only when /api/*
// reaches the frontend; a reverse proxy routing /api/ to port 5055 returns the API's 404.
export const FRONTEND_PROXY_PROBE_PATH = '/api/frontend-proxy'

export const PROXY_UPLOAD_DOCS_URL =
  'https://github.com/lfnovo/open-notebook/blob/main/docs/5-CONFIGURATION/reverse-proxy.md#upload-size-413-errors'

/** True for an empty or relative API URL, or one on the same origin as the page. */
export function apiSharesPageOrigin(apiUrl: string, pageOrigin: string): boolean {
  if (!apiUrl) return true
  try {
    return new URL(apiUrl, pageOrigin).origin === pageOrigin
  } catch {
    return false
  }
}

/**
 * True when API requests go through the frontend's /api/* rewrite. A same-origin
 * API URL is not enough: a reverse proxy may route /api/ straight to the API,
 * so ask the frontend's probe route. Any failure counts as a direct call.
 */
export async function uploadsUseFrontendProxy(
  apiUrl: string,
  pageOrigin: string,
  fetchFn: typeof fetch = fetch,
): Promise<boolean> {
  if (!apiSharesPageOrigin(apiUrl, pageOrigin)) return false
  try {
    const response = await fetchFn(`${apiUrl}${FRONTEND_PROXY_PROBE_PATH}`, { cache: 'no-store' })
    return response.ok
  } catch {
    return false
  }
}

/** Files the rewrite would cut off, if uploads go through it. */
export function filesTooLargeForProxy(files: File[]): File[] {
  return files.filter((file) => file.size > PROXY_MAX_UPLOAD_BYTES - MULTIPART_HEADROOM_BYTES)
}
