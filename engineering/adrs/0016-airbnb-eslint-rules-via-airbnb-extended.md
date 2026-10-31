---
category: architecture
status: proposed
date: 2026-10-31
---

# ADR-0016: Airbnb ESLint Rules via eslint-config-airbnb-extended

## Status

Proposed

## Date

2026-10-31

## Context

The client's lint rules are the Airbnb JavaScript style guide, which the GSA 18F Front-End Guide names and the SOW requires us to lint against with zero errors and warnings ([SOW §5.2](../../product/context/PA%20Compact%20Data%20System%20SOW%20-%20Focus%20Consulting.md), "Properly Styled Code"). Until now they came from `eslint-config-airbnb` 19 and `eslint-config-airbnb-typescript` 18 through `.eslintrc.cjs`.

Both packages have stopped. `eslint-config-airbnb` 19.0.4 (2021) is its last release and supports ESLint 8 and `eslint-plugin-react-hooks` 4. `eslint-config-airbnb-typescript` 18.0.0 (March 2024) is its last release, supports typescript-eslint 7, and configures two rules that typescript-eslint 8 deleted, so it cannot load on 8 at all. ESLint 10 removed the eslintrc format they are written in, and `eslint-config-next` 16 is flat-config only. Five open Dependabot pull requests (eslint 10, eslint-config-next 16, typescript-eslint 8, react-hooks 7) fail on one or both of them.

Against the current configuration, Airbnb accounts for 155 of the 275 active rules on a component file; the plugins' own recommended sets account for the rest. Formatting is Prettier's and is not among them.

## Decision

1. **The client's ESLint configuration is `eslint.config.mjs`** (flat config). `.eslintrc.cjs` is deleted.
2. **The Airbnb rules come from `eslint-config-airbnb-extended`'s `legacy` entry point**, which is written as a one-to-one port of `airbnb`, `airbnb/hooks`, and `airbnb-typescript` to flat config, with the plugins it needs bundled. `eslint-config-airbnb`, `eslint-config-airbnb-typescript`, and the direct dependencies that existed only to satisfy their peer ranges (`@typescript-eslint/eslint-plugin`, `@typescript-eslint/parser`, `eslint-plugin-import`, `eslint-plugin-jsx-a11y`, `eslint-plugin-react`, `eslint-plugin-react-hooks`) are removed.
3. **Next's rules come from `@next/eslint-plugin-next` directly** rather than `eslint-config-next`, which registers its own copies of the React, import, and a11y plugins under the same names and so cannot be combined with a config that already registers them.
4. **The deviations from Airbnb stay in the config file with their reasons**, as before. Three rules `eslint-config-next` used to switch on over Airbnb (`react/jsx-key`, `react/display-name`, `import/no-anonymous-default-export`) are switched on explicitly so the enforced set does not shrink.

## Pros and cons

### eslint-config-airbnb-extended, legacy mode (chosen)

- Pro: the same rule set, so the README's and the SOW's "Airbnb style guide" stays literally true, and the migration is a mechanical change reviewers can check by diffing the active rules.
- Pro: runs on ESLint 9, typescript-eslint 8, and react-hooks 7, which unblocks the Dependabot stream.
- Pro: fewer direct dependencies, since it bundles its plugins.
- Con: a community package with one maintainer, not Airbnb. Mitigation: it is a dev dependency with no runtime footprint, and the rules it ships are Airbnb's published ones, so a replacement is a config edit, not a code change.
- Con: its peer range is ESLint 9; ESLint 10 waits for its next major. Dependabot ignores ESLint majors until then.

### Keep the old packages through `FlatCompat`

- Pro: no new dependency.
- Con: solves only the config format. typescript-eslint and react-hooks stay pinned at 7 and 5 for as long as the Airbnb packages do, which is indefinitely.

### Recommended configs only, or a hand-picked subset of Airbnb

- Pro: no third-party style package at all; the config file is the whole policy.
- Con: drops or re-decides 155 rules in a PR whose purpose is a dependency upgrade, and weakens the claim against the 18F guide. Still open as a later change: trimming rules from a flat file is easy once on one.

## Consequences

- The ESLint dependencies are `eslint`, `eslint-config-airbnb-extended`, `@next/eslint-plugin-next`, `eslint-config-prettier`, `eslint-plugin-jsdoc`, and `eslint-plugin-storybook`.
- `next build` no longer lints: Next 14's build-time runner looks only for eslintrc files. CI's `lint` job is the gate, as it already was.
- `.github/dependabot.yml` ignores ESLint majors until `eslint-config-airbnb-extended` supports ESLint 10, with the reason beside the rule.
- The Dependabot pull requests for eslint-config-next 16, typescript-eslint 8, and react-hooks 7 are superseded by this change; the one for eslint 10 by the ignore rule.

## Related

- Constitution Principle I (new dependencies need an ADR).
- [SOW §5.2](../../product/context/PA%20Compact%20Data%20System%20SOW%20-%20Focus%20Consulting.md), "Properly Styled Code".
- [eslint-config-airbnb-extended](https://github.com/eslint-config/airbnb-extended), legacy config.
