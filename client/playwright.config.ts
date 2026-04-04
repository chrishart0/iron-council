import fs from "node:fs";
import path from "node:path";
import { defineConfig } from "@playwright/test";

const repoRoot = path.resolve(__dirname, "..");
const runtimeDir = path.join(repoRoot, ".playwright-tmp");
const databasePath = path.join(runtimeDir, "browser-smoke.db");
const envFilePath = path.join(runtimeDir, "browser-smoke.env");
const serverHost = "127.0.0.1";
const serverPort = "8100";
const clientHost = "127.0.0.1";
const clientPort = "3100";
const serverBootstrapCommand = [
  `IRON_COUNCIL_ENV_FILE='${envFilePath}' IRON_COUNCIL_SERVER_HOST='${serverHost}' IRON_COUNCIL_SERVER_PORT='${serverPort}' ./scripts/runtime-control.sh db-reset`,
  `IRON_COUNCIL_ENV_FILE='${envFilePath}' IRON_COUNCIL_MATCH_REGISTRY_BACKEND='db' IRON_COUNCIL_SERVER_HOST='${serverHost}' IRON_COUNCIL_SERVER_PORT='${serverPort}' ./scripts/runtime-control.sh server`
].join(" && ");

fs.mkdirSync(runtimeDir, { recursive: true });
fs.writeFileSync(
  envFilePath,
  [
    `DATABASE_URL=sqlite+pysqlite:///${databasePath}`,
    `IRON_COUNCIL_BROWSER_ORIGINS=http://${clientHost}:${clientPort}`
  ].join("\n") + "\n",
  "utf8"
);

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  retries: 0,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: `http://${clientHost}:${clientPort}`,
    browserName: "chromium",
    headless: true
  },
  webServer: [
    {
      command: `bash -euo pipefail -c ${JSON.stringify(serverBootstrapCommand)}`,
      cwd: repoRoot,
      url: `http://${serverHost}:${serverPort}/health`,
      reuseExistingServer: false,
      timeout: 120_000
    },
    {
      command: `bash -lc "IRON_COUNCIL_CLIENT_HOST='${clientHost}' IRON_COUNCIL_CLIENT_PORT='${clientPort}' ./scripts/runtime-control.sh client-start"`,
      cwd: repoRoot,
      url: `http://${clientHost}:${clientPort}/matches`,
      reuseExistingServer: false,
      timeout: 120_000
    }
  ]
});
