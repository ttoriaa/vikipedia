#!/usr/bin/env node

import { createHash } from "node:crypto";
import { mkdirSync, readFileSync, statSync, writeFileSync, existsSync, readdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { execSync } from "node:child_process";

function parseArgs(argv) {
  const out = {};
  for (let i = 2; i < argv.length; i += 1) {
    const token = argv[i];
    if (!token.startsWith("--")) continue;
    const key = token.slice(2);
    const next = argv[i + 1];
    if (!next || next.startsWith("--")) {
      out[key] = "true";
    } else {
      out[key] = next;
      i += 1;
    }
  }
  return out;
}

function toBool(value, fallback = false) {
  if (value === undefined || value === null || value === "") return fallback;
  return ["1", "true", "yes", "on"].includes(String(value).toLowerCase());
}

function loadJson(filePath, fallback) {
  try {
    return JSON.parse(readFileSync(filePath, "utf8"));
  } catch {
    return fallback;
  }
}

function ensureDir(filePath) {
  mkdirSync(dirname(filePath), { recursive: true });
}

function hashText(text) {
  return createHash("sha256").update(text, "utf8").digest("hex");
}

function hasFilesRecursively(dirPath) {
  const entries = readdirSync(dirPath, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = resolve(dirPath, entry.name);
    if (entry.isFile()) return true;
    if (entry.isDirectory() && hasFilesRecursively(fullPath)) return true;
  }
  return false;
}

function validatePath(pathLike) {
  const fullPath = resolve(pathLike);
  if (!existsSync(fullPath)) {
    throw new Error(`Required path not found: ${pathLike}`);
  }

  const st = statSync(fullPath);
  if (st.isFile() && st.size <= 0) {
    throw new Error(`Required file is empty: ${pathLike}`);
  }

  if (st.isDirectory() && !hasFilesRecursively(fullPath)) {
    throw new Error(`Required directory has no files: ${pathLike}`);
  }
}

function appendGithubOutput(key, value) {
  const outputFile = process.env.GITHUB_OUTPUT;
  if (!outputFile) return;
  writeFileSync(outputFile, `${key}=${value}\n`, { flag: "a" });
}

async function main() {
  const args = parseArgs(process.argv);
  const rssUrl = args["rss-url"] || process.env.RSS_URL;
  const updateCommand = args["update-command"] || process.env.UPDATE_COMMAND || "";
  const stateFile = args["state-file"] || process.env.STATE_FILE || ".cache/rss_state.json";
  const changedPathsRaw = args["changed-paths"] || process.env.CHANGED_PATHS || "";
  const dryRun = toBool(args["dry-run"] || process.env.DRY_RUN, false);

  if (!rssUrl) {
    throw new Error("Missing RSS URL. Pass --rss-url or RSS_URL.");
  }

  const statePath = resolve(stateFile);
  const prev = loadJson(statePath, {});

  const headers = {};
  if (prev.etag) headers["If-None-Match"] = prev.etag;
  if (prev.lastModified) headers["If-Modified-Since"] = prev.lastModified;

  const resp = await fetch(rssUrl, { headers });
  if (resp.status === 304) {
    console.log("RSS not changed (304).");
    appendGithubOutput("changed", "false");
    appendGithubOutput("http_status", "304");
    return;
  }

  if (!resp.ok) {
    throw new Error(`RSS request failed: HTTP ${resp.status}`);
  }

  const xmlText = await resp.text();
  const contentSha256 = hashText(xmlText);

  if (prev.content_sha256 && prev.content_sha256 === contentSha256) {
    console.log("RSS not changed (same content hash).");
    ensureDir(statePath);
    writeFileSync(
      statePath,
      JSON.stringify(
        {
          rss_url: rssUrl,
          etag: resp.headers.get("etag") || prev.etag || "",
          last_modified: resp.headers.get("last-modified") || prev.last_modified || "",
          content_sha256: contentSha256,
          checked_at: new Date().toISOString(),
        },
        null,
        2,
      ) + "\n",
      "utf8",
    );
    appendGithubOutput("changed", "false");
    appendGithubOutput("http_status", String(resp.status));
    return;
  }

  console.log("RSS changed, executing update command.");

  if (updateCommand) {
    if (dryRun) {
      console.log(`[dry-run] Skip command: ${updateCommand}`);
    } else {
      execSync(updateCommand, { stdio: "inherit", shell: true });
    }
  }

  const changedPaths = changedPathsRaw
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);

  if (!dryRun) {
    for (const p of changedPaths) {
      validatePath(p);
    }
  }

  ensureDir(statePath);
  writeFileSync(
    statePath,
    JSON.stringify(
      {
        rss_url: rssUrl,
        etag: resp.headers.get("etag") || "",
        last_modified: resp.headers.get("last-modified") || "",
        content_sha256: contentSha256,
        checked_at: new Date().toISOString(),
      },
      null,
      2,
    ) + "\n",
    "utf8",
  );

  appendGithubOutput("changed", "true");
  appendGithubOutput("http_status", String(resp.status));
  console.log("RSS sync completed.");
}

main().catch((err) => {
  console.error(err.message || err);
  appendGithubOutput("changed", "false");
  process.exit(1);
});
