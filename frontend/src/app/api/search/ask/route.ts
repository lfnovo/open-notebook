import type { NextRequest } from 'next/server'
import { sseProxy } from '../../_sse-proxy'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

export async function POST(req: NextRequest) {
  return sseProxy(req, '/api/search/ask')
}
