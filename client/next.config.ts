import path from "node:path";
import { fileURLToPath } from "node:url";
import type { NextConfig } from "next";

const clientRoot = path.dirname(fileURLToPath(import.meta.url));

const nextConfig: NextConfig = {
  turbopack: {
    root: clientRoot
  }
};

export default nextConfig;
