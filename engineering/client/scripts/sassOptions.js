// @ts-check
const sass = require("sass");

/**
 * Configure Sass to load USWDS assets, and expose a Sass function for setting the
 * correct relative path to image or font assets, when the site is hosted from a subdirectory.
 */
function sassOptions(basePath = "") {
  const loadPaths = [
    "./node_modules/@uswds",
    "./node_modules/@uswds/uswds/packages",
  ];
  return {
    // Sass's legacy API reads includePaths; its modern API reads loadPaths.
    includePaths: loadPaths,
    loadPaths,
    functions: {
      // Next.js calls this through Sass's legacy API, which passes each
      // argument; Storybook through the modern one, which passes an array.
      "add-base-path($path)": (arg) => {
        const value = Array.isArray(arg) ? arg[0].text : arg.getValue();
        return new sass.SassString(`${basePath}${value}`);
      },
    },
  };
}

module.exports = sassOptions;
