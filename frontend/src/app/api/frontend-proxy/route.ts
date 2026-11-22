import { PROXY_MAX_UPLOAD_MB } from '../../../lib/upload-limits'

// Lets the upload flow tell whether /api/* reaches this server (and its 100 MB
// rewrite limit) or is routed straight to the API. See src/lib/upload-proxy.ts.
export function GET() {
  return Response.json({ maxUploadMb: PROXY_MAX_UPLOAD_MB })
}
