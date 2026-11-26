import type { NextRequest } from 'next/server'
import { sseProxy } from '../../_sse-proxy'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

// A RAG ask streams for minutes while the models work. Without an explicit
// budget the platform default (60s on serverless, 30s on the dev proxy)
// would cut the stream in half. Seconds, aligned with the API timeout.
export const maxDuration = 300

export async function POST(req: NextRequest) {
  return sseProxy(req, '/api/search/ask')
}
