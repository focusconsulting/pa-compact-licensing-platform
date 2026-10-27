import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/tests/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    css: false,
    // The API client builds absolute URLs; the generated mocks match any host.
    env: { NEXT_PUBLIC_API_BASE_URL: "http://api.test" },
    coverage: {
      provider: "v8",
      reporter: ["text", "lcov"],
      // Constitution Principle III: 100% line and branch coverage.
      thresholds: {
        lines: 100,
        branches: 100,
        functions: 100,
        statements: 100,
      },
      include: ["src/**/*.{ts,tsx}"],
      exclude: [
        "src/tests/**",
        "src/**/*.test.{ts,tsx}",
        "src/**/*.stories.{ts,tsx}",
        "src/**/*.d.ts",
        "src/app/**/layout.tsx",
        "src/@types/**",
      ],
    },
  },
  resolve: {
    alias: {
      "/src": path.resolve(__dirname, "src"),
      src: path.resolve(__dirname, "src"),
    },
  },
});
