import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Allow workspace package source resolution
  transpilePackages: ["@atomadic/forge-ui-core"],
  experimental: {
    // PWA / installability
    optimizePackageImports: ["lucide-react", "motion"],
  },
  // We set deliberate CSP headers; SW lives at /sw.js
  async headers() {
    return [
      {
        source: "/sw.js",
        headers: [
          { key: "Content-Type", value: "application/javascript; charset=utf-8" },
          { key: "Cache-Control", value: "no-cache, no-store, must-revalidate" },
          { key: "Service-Worker-Allowed", value: "/" },
        ],
      },
    ];
  },
};

export default nextConfig;
