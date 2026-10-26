import type { StorybookConfig } from "@storybook/nextjs";
import { fileURLToPath } from "node:url";

const config: StorybookConfig = {
  stories: ["../src/**/*.mdx", "../src/**/*.stories.@(js|jsx|mjs|ts|tsx)"],
  addons: [
    "@storybook/addon-onboarding",
    "@storybook/addon-links",
    "@chromatic-com/storybook",
  ],
  framework: {
    name: "@storybook/nextjs",
    options: {
      nextConfigPath: fileURLToPath(
        new URL("../next.config.js", import.meta.url),
      ),
    },
  },
};
export default config;
