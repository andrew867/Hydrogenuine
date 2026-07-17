import path from "node:path";
import { fileURLToPath } from "node:url";

const rootDir = path.dirname(fileURLToPath(import.meta.url));
const uiKitDir = path.resolve(rootDir, "../ui/hg_ui_kit");

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  reactStrictMode: true,
  transpilePackages: ["hg_ui_kit"],
  experimental: {
    optimizePackageImports: ["@tanstack/react-query"]
  },
  images: {
    remotePatterns: [{ protocol: "https", hostname: "**" }]
  },
  webpack(config) {
    config.resolve.alias = {
      ...(config.resolve.alias || {}),
      "hg_ui_kit/tokens.css": path.resolve(uiKitDir, "src/tokens/tokens.css"),
      "hg_ui_kit/components.css": path.resolve(uiKitDir, "src/tokens/components.css"),
      hg_ui_kit: path.resolve(uiKitDir, "dist/index.js"),
    };
    if (process.env.ANALYZE) {
      // Lazy require to avoid dependency unless needed
      const { BundleAnalyzerPlugin } = require("webpack-bundle-analyzer");
      config.plugins.push(new BundleAnalyzerPlugin({ analyzerMode: "static" }));
    }
    return config;
  }
};

export default nextConfig;
