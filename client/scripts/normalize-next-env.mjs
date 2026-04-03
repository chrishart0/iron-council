import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const clientRoot = path.resolve(scriptDir, "..");
const nextEnvPath = path.join(clientRoot, "next-env.d.ts");
const canonicalImport = 'import "./.next/types/routes.d.ts";';
const devImport = 'import "./.next/dev/types/routes.d.ts";';

export function normalizeNextEnv() {
  if (!fs.existsSync(nextEnvPath)) {
    return false;
  }

  const current = fs.readFileSync(nextEnvPath, "utf8");
  if (!current.includes(devImport)) {
    return false;
  }

  fs.writeFileSync(nextEnvPath, current.replace(devImport, canonicalImport));
  return true;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  normalizeNextEnv();
}
