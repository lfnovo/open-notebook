import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enable standalone output for optimized Docker deployment
  output: "standalone",

  // API rewrites for production deployment
  // Rewrites /api/* requests to the backend API server
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:5055/api/:path*",
      },
    ];
  },
};

export default nextConfig;
