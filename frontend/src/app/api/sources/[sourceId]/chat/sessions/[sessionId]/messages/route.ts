import type { NextRequest } from 'next/server'
import { sseProxy } from '../../../../../../_sse-proxy'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ sourceId: string; sessionId: string }> }
) {
  const { sourceId, sessionId } = await params
  return sseProxy(
    req,
    `/api/sources/${encodeURIComponent(sourceId)}/chat/sessions/${encodeURIComponent(sessionId)}/messages`
  )
}
