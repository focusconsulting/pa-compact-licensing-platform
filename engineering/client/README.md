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

Storybook can be started by running `pnpm storybook`
<!--
Fri Apr 17 08:58:34 EDT 2026
-->

## The API client

`src/api/schema.d.ts` (types) and `src/api/mocks.ts` (MSW handlers) are
generated from `engineering/api/openapi.json`. After changing an API route,
run `just generate` from the repository root and commit the result; CI fails
while they differ ([ADR-0013](../adrs/0013-generated-api-client-and-mocks.md)).

## Key dependencies

| Package                                       | Purpose                                                           | Docs                      |
| --------------------------------------------- | ----------------------------------------------------------------- | ------------------------- |
| [openapi-typescript](https://openapi-ts.dev/) | Generates `src/api/schema.d.ts` from the API's OpenAPI document   | <https://openapi-ts.dev/> |
| [MSW](https://mswjs.io/)                      | Answers API calls with the generated mocks in tests and Storybook | <https://mswjs.io/docs/>  |
