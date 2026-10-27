# Client

## Developer Setup

Please make sure you have followed the [prerequisites](../../README.md#prerequisites)
in the root README.

1. Copy the local settings: `cp .env.example .env`. These are public
   `NEXT_PUBLIC_*` values only; never put secrets in them
1. Run `pnpm install`
1. Run `pnpm dev`
1. Verify that <http://localhost:3000> loads

## Storybook

Storybook can be started by running `pnpm storybook`. Every story is signed in
(`.storybook/mocks/auth.ts`), and its API calls go to the Prism mock on
<http://localhost:4010>: start it first with `just mock-api` from the
repository root, or set `STORYBOOK_API_BASE_URL` to use another API.
<!--
Fri Apr 17 08:58:34 EDT 2026
-->

## The API client

`src/api/schema.d.ts` is generated from `engineering/api/openapi.json`. After
changing an API route, run `just generate` from the repository root and commit
the result; CI fails while they differ
([ADR-0013](../adrs/0013-generated-api-client-and-mocks.md)).

To run the client with no API, start the mock from the repository root with
`just mock-api`, then `NEXT_PUBLIC_API_BASE_URL=http://localhost:4010 pnpm dev`.
Prism answers each route with the examples in the document.

## Key dependencies

| Package                                                | Purpose                                                                                                             | Docs                                    |
| ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------- | --------------------------------------- |
| [openapi-typescript](https://openapi-ts.dev/)          | Generates `src/api/schema.d.ts` from the API's OpenAPI document                                                     | <https://openapi-ts.dev/>               |
| [openapi-fetch](https://openapi-ts.dev/openapi-fetch/) | The typed API client in `src/lib/api.ts`                                                                            | <https://openapi-ts.dev/openapi-fetch/> |
| [Prism](https://github.com/stoplightio/prism) (Docker) | `just mock-api`: a mock API from the document, never installed in the app                                           | <https://docs.stoplight.io/docs/prism/> |
| [webpack](https://webpack.js.org/)                     | Pinned below 5.101 for Storybook: later versions' `DefinePlugin` taps a parser hook Next 14's bundled webpack lacks | <https://webpack.js.org/>               |
