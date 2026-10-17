import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ["@reel-studio/timeline-schema"],
  ...(process.env.RS_BUILD_SINGLE_WORKER === "1" ? { experimental: { cpus: 1 } } : {}),
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
