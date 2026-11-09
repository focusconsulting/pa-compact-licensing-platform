// @ts-check

/**
 * Configure Sass to load USWDS assets, and give it the base path for image and
 * font URLs, when the site is hosted from a subdirectory.
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
    // A variable rather than a custom function: Turbopack accepts only
    // serializable Sass options.
    additionalData: `$base-path: "${basePath}";`,
  };
}

module.exports = sassOptions;
