// Serves the client's static export under the Content-Security-Policy CloudFront sends
// in AWS, so a page that breaks the policy fails here and not on a deployed environment.
// Usage: node serve-client.mts <port>, after `pnpm build` in ../client.
import { spawn } from "node:child_process";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";

const client = path.resolve(import.meta.dirname, "../client");
const policyFile = path.resolve(
  import.meta.dirname,
  "../infrastructure/iac/components/app/opentofu/content-security-policy.json",
);

// Locally the API, the Cognito mock, and RustFS are other ports on localhost. In AWS
// they are the site itself, Cognito, and the documents bucket, which headers.tf adds
// to the same two directives.
const LOCAL_ORIGINS: Record<string, string[]> = {
  "connect-src": ["http://localhost:*"],
  "form-action": ["http://localhost:*"],
};

const port = process.argv[2];
if (!port) {
  throw new Error("Usage: node serve-client.mts <port>");
}
if (!existsSync(path.join(client, "out"))) {
  throw new Error("No static export to serve: run `pnpm build` in engineering/client, or `just e2e`.");
}

const shared = JSON.parse(readFileSync(policyFile, "utf8")) as Record<string, string[]>;
const policy = Object.entries(shared)
  .map(([directive, sources]) => [directive, ...sources, ...(LOCAL_ORIGINS[directive] ?? [])].join(" "))
  .join("; ");

const config = path.join(tmpdir(), `licensing-client-serve-${port}.json`);
writeFileSync(
  config,
  JSON.stringify({
    headers: [{ source: "**", headers: [{ key: "Content-Security-Policy", value: policy }] }],
  }),
);

const serve = spawn("pnpm", ["exec", "serve", "out", "-l", port, "-c", config], {
  cwd: client,
  stdio: "inherit",
});
serve.on("exit", (code) => process.exit(code ?? 1));
