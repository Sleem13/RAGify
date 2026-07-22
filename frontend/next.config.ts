import type { NextConfig } from "next";

const backendUrl = process.env.BACKEND_URL || "http://localhost:9999";

const nextConfig: NextConfig = {
  output: "standalone",
  allowedDevOrigins: ["127.0.0.1", "localhost"],
  experimental: {
    // PDF extraction and local embedding can take longer than Next's 30s proxy default.
    proxyTimeout: 180_000,
    // Keep multipart uploads compatible with the backend's 50 MB file limit.
    proxyClientMaxBodySize: "55mb",
  },
  async rewrites() {
    return [
      {
        source: "/api/backend/:path*",
        destination: `${backendUrl}/:path*`,
      },
    ];
  },
};

export default nextConfig;
