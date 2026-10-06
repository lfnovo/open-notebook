// Upload size limit of the Next.js /api/* rewrite (see next.config.ts).
// No imports on purpose: next.config.ts loads this file outside the app bundle.
export const PROXY_MAX_UPLOAD_MB = 100
export const PROXY_MAX_UPLOAD_BYTES = PROXY_MAX_UPLOAD_MB * 1024 * 1024
