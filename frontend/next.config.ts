import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        // Proxy all requests starting with /api/proxy to the EC2 backend
        source: "/api/proxy/:path*",
        destination: "http://3.110.183.158/:path*",
      },
    ];
  },
};

export default nextConfig;
