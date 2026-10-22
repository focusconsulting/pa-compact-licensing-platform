// The GSA 18F front-end guide's choice: the Airbnb style guide, with Prettier
// for formatting (SOW §5.2 "Properly Styled Code"). Deviations are listed
// below with their reasons; CI runs with --max-warnings 0.
module.exports = {
  root: true,
  parserOptions: {
    project: "./tsconfig.json",
  },
  extends: [
    "airbnb",
    "airbnb/hooks",
    "airbnb-typescript",
    "next/core-web-vitals",
    "plugin:storybook/recommended",
    "prettier",
  ],
  rules: {
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
          "*.config.{js,ts}",
          ".storybook/**",
        ],
      },
    ],
  },
};
