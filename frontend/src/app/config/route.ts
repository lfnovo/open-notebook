import { NextRequest, NextResponse } from 'next/server'

// Basic hostname/IPv4 validation (letters, digits, dots, hyphens) plus a
// bracketed-IPv6-literal form. Host and X-Forwarded-Proto are client-
// controlled; behind a reverse proxy that forwards them untrusted, an
// unvalidated value here could redirect the browser's subsequent API
// traffic (including the auth bearer token - see lib/api/client.ts) to an
// attacker-chosen host. Reject anything that isn't syntactically a
// hostname/IP before it's used to build the URL the client will trust.
const HOSTNAME_PATTERN = /^[a-zA-Z0-9.-]+$/
const IPV6_LITERAL_PATTERN = /^\[[0-9a-fA-F:]+\]$/

function isValidHostname(hostname: string): boolean {
  return (
    hostname.length > 0 &&
    hostname.length <= 253 &&
    (HOSTNAME_PATTERN.test(hostname) || IPV6_LITERAL_PATTERN.test(hostname))
  )
}

// Strip the optional port from a Host header, keeping the hostname (with
// brackets for an IPv6 literal). Deliberately NOT `new URL()`: the URL
// parser would "helpfully" extract the host from userinfo/path payloads
// (e.g. `legit@evil.com` -> `evil.com`), defeating the strict validation
// below. A bracketed IPv6 literal (`[::1]` / `[::1]:5055`) can't be split
// on the first colon, so it's handled explicitly; everything else is a
// hostname/IPv4 where the first colon begins the port. Anything malformed
// returns null and falls back to localhost.
function extractHostname(hostHeader: string): string | null {
  if (hostHeader.startsWith('[')) {
    const end = hostHeader.indexOf(']')
    if (end === -1) return null
    const afterBracket = hostHeader.slice(end + 1)
    // Only an optional `:port` may follow the closing bracket.
    if (afterBracket !== '' && !/^:\d+$/.test(afterBracket)) return null
    return hostHeader.slice(0, end + 1) // includes the brackets
  }
  return hostHeader.split(':')[0]
}

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
    return NextResponse.json({
      apiUrl: envApiUrl,
    })
  }

  // Priority 2: Auto-detect from request headers - but only for a bare IP
  // literal (e.g. a LAN address). A named host (domain, tunnel hostname,
  // "localhost") almost never has the API reachable on the same host at
  // :5055 externally (reverse proxies/tunnels commonly expose only the
  // frontend's port) - relative paths through this app's own /api rewrite
  // (Priority 3 below) work in every case, local or remote, and avoid
  // CORS/port-mapping complexity entirely, so they're preferred whenever
  // we can't be sure a same-host :5055 is actually reachable.
  try {
    const rawProto = request.headers.get('x-forwarded-proto') ||
                  request.nextUrl.protocol.replace(':', '') ||
                  'http'
    const proto = rawProto === 'https' ? 'https' : 'http'

    const hostHeader = request.headers.get('host')

    if (hostHeader) {
      const hostname = extractHostname(hostHeader)
      const isIpLiteral = hostname !== null && (
        IPV6_LITERAL_PATTERN.test(hostname) || /^\d{1,3}(\.\d{1,3}){3}$/.test(hostname)
      )

      if (hostname && isIpLiteral && isValidHostname(hostname)) {
        const apiUrl = `${proto}://${hostname}:5055`

        console.log(`[runtime-config] Auto-detected API URL: ${apiUrl} (proto=${proto}, host=${hostHeader})`)

        return NextResponse.json({
          apiUrl,
        })
      }
    }
  } catch (error) {
    console.error('[runtime-config] Auto-detection failed:', error)
  }

  // Priority 3: Relative path - browser calls this app's own origin, and
  // next.config.ts rewrites /api/* to INTERNAL_API_URL server-side. Works
  // for localhost, LAN hostnames, and tunnels (ngrok, etc.) alike.
  console.log('[runtime-config] Using relative path (proxied via this app\'s /api rewrite)')
  return NextResponse.json({
    apiUrl: '',
  })
}
