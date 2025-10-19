import { NextResponse } from 'next/server'

/**
 * Runtime Configuration Endpoint
 *
 * This endpoint provides server-side environment variables to the client at runtime.
 * This solves the NEXT_PUBLIC_* limitation where variables are baked into the build.
 *
 * Users can now set API_URL in their docker.env and it will be picked up at runtime,
 * allowing the same Docker image to work in different deployment scenarios.
 */
export async function GET() {
  // Priority:
  // 1. API_URL from environment (set by user at runtime)
  // 2. NEXT_PUBLIC_API_URL from build time (fallback)
  // 3. Default to localhost:5055
  const apiUrl = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5055'

  return NextResponse.json({
    apiUrl,
  })
}
