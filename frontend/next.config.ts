import type { NextConfig } from "next";

const backendUrl = process.env.BACKEND_URL || "http://localhost:9999";
const isGitHubPagesBuild = process.env.GITHUB_PAGES === "true";
const repositoryName = process.env.GITHUB_REPOSITORY?.split("/")[1] || "";
const isUserOrOrganizationSite = repositoryName.endsWith(".github.io");
const basePath =
  isGitHubPagesBuild && repositoryName && !isUserOrOrganizationSite
    ? `/${repositoryName}`
    : "";

const nextConfig: NextConfig = {
  output: isGitHubPagesBuild ? "export" : "standalone",
  basePath,
  assetPrefix: basePath,
  trailingSlash: isGitHubPagesBuild,
  images: {
    unoptimized: isGitHubPagesBuild,
  },
  allowedDevOrigins: ["127.0.0.1", "localhost"],
  ...(isGitHubPagesBuild
    ? {}
    : {
        experimental: {
          // PDF extraction and local embedding can take longer than Next's proxy default.
          proxyTimeout: 180_000,
          // Keep multipart uploads compatible with the backend's file limit.
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
      }),
};

export default nextConfig;
