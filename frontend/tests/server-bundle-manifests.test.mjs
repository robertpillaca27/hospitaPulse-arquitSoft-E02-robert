// Runtime validation coverage for: Next.js server chunk consistency.
import { expect, it } from "vitest";
import { existsSync, readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const serverDirectory = fileURLToPath(new URL("../.next/server/", import.meta.url));
const traceManifests = findTraceManifests(serverDirectory);

function findTraceManifests(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const entryPath = path.join(directory, entry.name);
    if (entry.isDirectory()) return findTraceManifests(entryPath);
    return entry.name.endsWith(".js.nft.json") ? [entryPath] : [];
  });
}

it.skipIf(traceManifests.length === 0)("all traced Next.js server bundle files exist", () => {
  const missingFiles = traceManifests.flatMap((manifestPath) => {
    const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
    return manifest.files
      .filter((file) => !path.isAbsolute(file))
      .filter((file) => !existsSync(path.resolve(path.dirname(manifestPath), file)))
      .map((file) => `${path.relative(serverDirectory, manifestPath)} -> ${file}`);
  });

  expect(missingFiles, "every traced server chunk and dependency should exist").toEqual([]);
});
