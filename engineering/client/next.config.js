// @ts-check
const sassOptions = require("./scripts/sassOptions");

/**
 * Configure the base path for the app. Useful if you're deploying to a subdirectory (like GitHub Pages).
 * If this is defined, you'll need to set the base path anywhere you use relative paths, like in
 * `<a>`, `<img>`, or `<Image>` tags. Next.js handles this for you automatically in `<Link>` tags.
 * @see https://nextjs.org/docs/api-reference/next.config.js/basepath
 * @example "/test" results in "localhost:3000/test" as the index page for the app
 */
const basePath = process.env.NEXT_PUBLIC_BASE_PATH;
const appSassOptions = sassOptions(basePath);

const isDev = process.env.NODE_ENV !== "production";

/** @type {import('next').NextConfig} */
const nextConfig = {
  basePath,
  reactStrictMode: true,
  // Static export for production (S3/CloudFront). Omitted in dev so that rewrites work.
  // https://nextjs.org/docs/app/api-reference/next-config-js/output
  ...(isDev ? {} : { output: "export" }),
  sassOptions: appSassOptions,
  // Proxy /api/* to the local FastAPI server during development.
  // In production the browser calls NEXT_PUBLIC_API_BASE_URL directly.
  async rewrites() {
    if (!isDev) return [];
    const apiBase =
      process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${apiBase}/api/:path*`,
      },
    ];
  },
  // Continue to support older browsers (ES5)
  transpilePackages: [
    // https://github.com/trussworks/react-uswds/issues/2605
    "@trussworks/react-uswds",
  ],
};

module.exports = nextConfig;
