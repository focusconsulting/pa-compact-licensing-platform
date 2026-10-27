import "../src/styles/styles.scss";

/**
 * @file Setup the toolbar, styling, and global context for each Storybook story.
 * @see https://storybook.js.org/docs/configure#configure-story-rendering
 */
import { Preview } from "@storybook/nextjs";

import { AuthProvider } from "../src/contexts/AuthContext";

const parameters = {
  nextjs: {
    appDirectory: true,
  },
  controls: {
    matchers: {
      color: /(background|color)$/i,
      date: /Date$/,
    },
  },
  options: {
    storySort: {
      method: "alphabetical",
      order: [
        "Welcome",
        "Core",
        // Storybook infers the title when not explicitly set, but is case-sensitive
        // so we need to explicitly set both casings here for this to properly sort.
        "Components",
        "components",
        "Templates",
        "Pages",
        "pages",
      ],
    },
  },
};

const preview: Preview = {
  parameters,
  decorators: [
    (Story) => (
      <AuthProvider>
        <Story />
      </AuthProvider>
    ),
  ],
};

export default preview;
