import { NextRequest, NextResponse } from 'next/server'

/**
 * Runtime Configuration Endpoint
 *
 * This endpoint provides server-side environment variables to the client at runtime.
 * This solves the NEXT_PUBLIC_* limitation where variables are baked into the build.
 *
 * Environment Variables:
 * - API_URL: Where the browser/client should make API requests (public/external URL)
 * - INTERNAL_API_URL: Where Next.js server-side should proxy API requests (internal URL)
 *   Default: http://localhost:5055 (used by Next.js rewrites in next.config.ts)
 *
 * Why two different variables?
 * - API_URL: Used by browser clients, can be https://your-domain.com or http://server-ip:5055
 * - INTERNAL_API_URL: Used by Next.js rewrites for server-side proxying, typically http://localhost:5055
 *
 * Auto-detection logic for API_URL:
 * 1. If API_URL env var is set, use it (explicit override)
 * 2. Otherwise, detect from incoming HTTP request headers (zero-config)
 * 3. Fallback to localhost:5055 if detection fails
 *
 * This allows the same Docker image to work in different deployment scenarios.
 */
export async function GET(request: NextRequest) {
  // Priority 1: Check if API_URL is explicitly set
  const envApiUrl = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL

  if (envApiUrl) {
    return NextResponse.json({ apiUrl: envApiUrl })
  }

  // Priority 2: Auto-detect from the incoming request host so it works on any IP/hostname.
  // This means the browser will call the backend on the same host but port 5055,
  // which avoids routing through the Next.js proxy (and its timeout) for long requests.
  try {
    const host = request.headers.get('host') || ''
    // Strip port from host, then append the backend port
    const hostname = host.split(':')[0]
    if (hostname) {
      // Always return direct backend URL (including localhost) to bypass Next.js proxy timeout
      return NextResponse.json({ apiUrl: `http://${hostname}:5055` })
    }
  } catch {
    // fall through to empty string
  }

  // Use empty string so the frontend uses Next.js rewrites (/api/* proxy)
  // This avoids CORS issues when frontend and backend are on different ports
  return NextResponse.json({ apiUrl: '' })
}
