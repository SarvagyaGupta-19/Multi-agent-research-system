import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        // Proxy all requests starting with /api/proxy to the EC2 backend
        source: "/api/proxy/:path*",
        destination: "http://15.207.114.224:8000/:path*",
      },
    ];
  },
};

export default nextConfig;
