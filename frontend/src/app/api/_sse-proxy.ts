import type { NextRequest } from 'next/server'

const INTERNAL_API_URL = process.env.INTERNAL_API_URL || 'http://localhost:5055'

const SSE_HEADERS = {
  'Content-Type': 'text/event-stream; charset=utf-8',
  'Cache-Control': 'no-cache, no-transform',
  Connection: 'keep-alive',
  'X-Accel-Buffering': 'no',
}

export async function sseProxy(req: NextRequest, upstreamPath: string) {
  const body = await req.text()
  const auth = req.headers.get('authorization')

  let upstream: Response
  try {
    upstream = await fetch(`${INTERNAL_API_URL}${upstreamPath}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(auth ? { Authorization: auth } : {}),
        Accept: 'text/event-stream',
      },
      body,
      cache: 'no-store',
      // Forward the browser's abort signal: without it, clicking Stop during
      // the model's prefill (before the first byte) leaves the upstream request
      // — and the generation behind it — running.
      signal: req.signal,
    })
  } catch (err) {
    // A Stop during prefill aborts the fetch itself; the stream is over, not a
    // route error. An empty body ends the client's reader quietly.
    if (req.signal.aborted) {
      return new Response('', { status: 200, headers: SSE_HEADERS })
    }
    throw err
  }

  if (!upstream.ok || !upstream.body) {
    return new Response(upstream.body, {
      status: upstream.status,
      headers: { 'Content-Type': upstream.headers.get('content-type') ?? 'application/json' },
    })
  }

  return new Response(upstream.body, {
    status: 200,
    headers: SSE_HEADERS,
  })
}
