import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Minimal production server for Docker (server.js + traced deps).
  output: "standalone",
};

export default nextConfig;
