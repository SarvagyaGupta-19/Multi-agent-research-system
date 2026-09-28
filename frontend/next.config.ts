import type { NextConfig } from "next";

// BP-15: Backend URL configurable via env var.
// Local dev: BACKEND_URL defaults to http://127.0.0.1:8000 (same machine)
// Production: set BACKEND_URL=https://your-api-server.com in Vercel dashboard
const backendUrl = process.env.BACKEND_URL || "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        // Proxy all requests starting with /api/proxy to the backend
        source: "/api/proxy/:path*",
        destination: `${backendUrl}/:path*`,
      },
    ];
  },
};

export default nextConfig;
