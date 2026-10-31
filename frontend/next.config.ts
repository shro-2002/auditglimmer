import type { NextConfig } from "next";

// Fully client-rendered SPA against an external FastAPI backend, so Cache Components /
// partial prefetching (template defaults) are disabled: no server data fetching happens here.
const nextConfig: NextConfig = {
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
