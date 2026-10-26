import type { StorybookConfig } from "@storybook/nextjs";
import { fileURLToPath } from "node:url";

const AUTH = fileURLToPath(new URL("../src/lib/auth.ts", import.meta.url));
const SIGNED_IN = fileURLToPath(new URL("mocks/auth.ts", import.meta.url));

type Tap<T> = { tap: (name: string, callback: (arg: T) => void) => void };
type Compiler = {
  hooks: {
    normalModuleFactory: Tap<{
      hooks: { afterResolve: Tap<{ createData: { resource?: string } }> };
    }>;
  };
};

/**
 * Swaps `src/lib/auth` for `mocks/auth.ts` after it resolves, so every story is
 * signed in. An alias would never apply: the tsconfig paths resolver handles
 * `src/...` first.
 */
class SignedInSession {
  // Storybook's webpack types differ from the installed webpack's, so the
  // compiler is typed by the two hooks this uses.
  // eslint-disable-next-line class-methods-use-this
  apply(compiler: Compiler) {
    compiler.hooks.normalModuleFactory.tap("SignedInSession", (factory) => {
      factory.hooks.afterResolve.tap("SignedInSession", (resolveData) => {
        const created = resolveData.createData;
        if (created.resource === AUTH) created.resource = SIGNED_IN;
      });
    });
  }
}

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
  // The app's assets (USWDS fonts), and MSW's service worker, kept out of the
  // app's public/ so it never ships.
  staticDirs: ["../public", "./public"],
  webpackFinal: async (webpackConfig) => {
    webpackConfig.plugins?.push(new SignedInSession());
    return webpackConfig;
  },
};
export default config;
