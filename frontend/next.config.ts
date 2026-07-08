import type { NextConfig } from "next";
import path from "path";
import { fileURLToPath } from "url";

// Next.js walks up the tree and can pick a parent lockfile (e.g. ~/package-lock.json)
// as the Turbopack root, which breaks resolution of frontend/node_modules packages
// like react-syntax-highlighter.
const frontendRoot = path.dirname(fileURLToPath(import.meta.url));

const nextConfig: NextConfig = {
  turbopack: {
    root: frontendRoot,
    resolveAlias: {
      tailwindcss: path.join(frontendRoot, "node_modules/tailwindcss"),
      "@tailwindcss/typography": path.join(
        frontendRoot,
        "node_modules/@tailwindcss/typography"
      ),
      "@tailwindcss/postcss": path.join(
        frontendRoot,
        "node_modules/@tailwindcss/postcss"
      ),
    },
  },
  outputFileTracingRoot: frontendRoot,

  // Enable standalone output for optimized Docker deployment
  output: "standalone",

  // Experimental features
  // Type assertion needed: proxyClientMaxBodySize is valid in Next.js 15 but types lag behind
  experimental: {
    // PostCSS/Tailwind resolve from frontend/ when a parent lockfile (e.g. ~/package-lock.json)
    // would otherwise make Turbopack treat the repo root as the workspace.
    turbopackLocalPostcssConfig: true,
    // Increase proxy body size limit for file uploads (default is 10MB)
    // This allows larger files to be uploaded through the /api/* rewrite proxy to FastAPI
    proxyClientMaxBodySize: '100mb',
  } as NextConfig['experimental'],

  // API Rewrites: Proxy /api/* requests to FastAPI backend
  // This simplifies reverse proxy configuration - users only need to proxy to port 8502
  // Next.js handles internal routing to the API backend on port 5055
  async rewrites() {
    // INTERNAL_API_URL: Where Next.js server-side should proxy API requests
    // Default: http://localhost:5055 (single-container deployment)
    // Override for multi-container: INTERNAL_API_URL=http://api-service:5055
    const internalApiUrl = process.env.INTERNAL_API_URL || 'http://localhost:5055'

    console.log(`[Next.js Rewrites] Proxying /api/* to ${internalApiUrl}/api/*`)

    return [
      {
        source: '/api/:path*',
        destination: `${internalApiUrl}/api/:path*`,
      },
    ]
  },
};

export default nextConfig;
