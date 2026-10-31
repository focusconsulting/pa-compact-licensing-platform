// The GSA 18F front-end guide's choice: the Airbnb style guide, with Prettier
// for formatting (SOW §5.2 "Properly Styled Code"). Airbnb's own configs
// stopped at ESLint 8, so the rules come from eslint-config-airbnb-extended's
// legacy entry point, a one-to-one port of them (ADR-0016). Deviations are
// listed below with their reasons; CI runs with --max-warnings 0.
import nextPlugin from "@next/eslint-plugin-next";
import { configs as airbnb } from "eslint-config-airbnb-extended/legacy";
import prettier from "eslint-config-prettier";
import jsdoc from "eslint-plugin-jsdoc";
import storybook from "eslint-plugin-storybook";
import { defineConfig, globalIgnores } from "eslint/config";

export default defineConfig([
  // Written by `pnpm generate`; CI fails when it differs from the API.
  globalIgnores(["src/api/schema.d.ts"]),
  ...airbnb.react.recommended,
  ...airbnb.react.hooks,
  ...airbnb.react.typescript,
  nextPlugin.configs["core-web-vitals"],
  ...storybook.configs["flat/recommended"],
  prettier,
  {
    plugins: { jsdoc },
    rules: {
      // Next's automatic JSX runtime imports React itself, and TypeScript
      // types the props.
      "react/react-in-jsx-scope": "off",
      "react/prop-types": "off",
      // Airbnb leaves these off; eslint-config-next used to turn them on, and
      // Fast Refresh and the React devtools need named components.
      "react/jsx-key": "error",
      "react/display-name": "error",
      "import/no-anonymous-default-export": "error",
      // TypeScript optional props make undefined explicit, and React 19 drops
      // defaultProps for function components.
      "react/require-default-props": "off",
      // Named exports keep imports stable when things are renamed or moved.
      "import/prefer-default-export": "off",
      // The client is a static export, where next/image cannot optimise images.
      "@next/next/no-img-element": "off",
      // react-hook-form wires fields by spreading register() and the form into these.
      "react/jsx-props-no-spreading": [
        "error",
        { exceptions: ["FormProvider", "TextInput"] },
      ],
      // Every exported function and component says what it does (2xz.4).
      "jsdoc/require-jsdoc": [
        "error",
        {
          publicOnly: true,
          require: {
            FunctionDeclaration: true,
            ArrowFunctionExpression: true,
            FunctionExpression: true,
            ClassDeclaration: true,
          },
        },
      ],
      // `void promise;` marks a promise deliberately left floating.
      "no-void": ["error", { allowAsStatement: true }],
      "import/extensions": [
        "error",
        "ignorePackages",
        { ts: "never", tsx: "never" },
      ],
      "import/no-extraneous-dependencies": [
        "error",
        {
          devDependencies: [
            "**/*.test.{ts,tsx}",
            "src/tests/**",
            "**/*.stories.{ts,tsx}",
            "*.config.{js,mjs,ts}",
            ".storybook/**",
          ],
        },
      ],
    },
  },
  {
    files: ["**/*.test.{ts,tsx}", "src/tests/**", "**/*.stories.{ts,tsx}"],
    rules: { "jsdoc/require-jsdoc": "off" },
  },
]);
