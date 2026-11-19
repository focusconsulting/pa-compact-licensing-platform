import { defineConfig, devices } from "@playwright/test";

const CLIENT_PORT = 3200;

// Runs against the API and local services of `just up`, with the client's static export
// served under the deployed Content-Security-Policy (serve-client.mts), or against
// wherever E2E_BASE_URL points.
export default defineConfig({
  testDir: "tests",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: process.env.E2E_BASE_URL ?? `http://localhost:${CLIENT_PORT}`,
    trace: "retain-on-failure",
  },
  webServer: process.env.E2E_BASE_URL
    ? undefined
    : {
        command: `node serve-client.mts ${CLIENT_PORT}`,
        url: `http://localhost:${CLIENT_PORT}/login`,
        // A server left from an earlier run could be serving an older build.
        reuseExistingServer: false,
      },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
