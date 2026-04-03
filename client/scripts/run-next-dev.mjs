import path from "node:path";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";

import { normalizeNextEnv } from "./normalize-next-env.mjs";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const clientRoot = path.resolve(scriptDir, "..");
const nextBin = path.join(clientRoot, "node_modules", "next", "dist", "bin", "next");
const child = spawn(process.execPath, [nextBin, "dev", ...process.argv.slice(2)], {
  cwd: clientRoot,
  stdio: "inherit",
});

let cleanedUp = false;

function cleanupAndExit(code, signal) {
  if (!cleanedUp) {
    cleanedUp = true;
    normalizeNextEnv();
  }

  if (signal === "SIGINT") {
    process.exit(130);
    return;
  }

  if (signal === "SIGTERM") {
    process.exit(143);
    return;
  }

  process.exit(code ?? 0);
}

function forwardSignal(signal) {
  if (child.killed) {
    return;
  }

  child.kill(signal);
}

process.on("SIGINT", () => {
  forwardSignal("SIGINT");
});

process.on("SIGTERM", () => {
  forwardSignal("SIGTERM");
});

child.on("exit", (code, signal) => {
  cleanupAndExit(code, signal);
});

child.on("error", (error) => {
  console.error(error);
  cleanupAndExit(1);
});
