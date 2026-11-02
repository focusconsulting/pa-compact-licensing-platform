# Design tokens

The names screens may use for colour, type, spacing, and radius. A token is a USWDS theme token, written as USWDS writes it: `"primary-dark"`, spacing `2`, type `"lg"`, radius `"md"`. It is set through its `$theme-*` setting in [`_uswds-theme.scss`](../../client/src/styles/_uswds-theme.scss) and read through USWDS functions and mixins (`color()`, `units()`, `u-*`, `typeset()`, `radius()`). Project SCSS holds no hex, `px`, or font-weight literal. The only names the project adds are the five status-tag tones.

Values are USWDS defaults, as placeholders, until the Commission's brand assets arrive (Q-09 in [`mvp-ticket-breakdown.md`](../../../product/backlog/mvp-ticket-breakdown.md#6-sprint-1--questions-for-the-client)). A new value changes a setting, not a name. Storybook's Design/Theme stories render every token with its current value.

The Figma Parts Library is the USWDS Figma kit, which names a family's base grade `medium`: Figma's `theme/color/primary/medium` is `primary` here.

## Colour

| Role | Tokens | Setting |
|---|---|---|
| Brand | `primary-lighter`, `primary-light`, `primary`, `primary-vivid`, `primary-dark`, `primary-darker` | `$theme-color-primary-*` |
| Secondary actions | `secondary-lighter`, `secondary-light`, `secondary`, `secondary-dark`, `secondary-darker` | `$theme-color-secondary-*` |
| Text, borders, surfaces | `base-lightest`, `base-lighter`, `base-light`, `base`, `base-dark`, `base-darker`, `base-darkest`, `ink`, `white` | `$theme-color-base-*`, `$theme-color-ink` |
| State | `info-*`, `success-*`, `warning-*`, `error-*` (`lighter`, `light`, base, `dark`, `darker`), `emergency` | `$theme-color-{state}-*` |

State colours are not rebranded, so their meaning stays recognisable. The `accent-cool` and `accent-warm` families are unused; a screen that needs one asks first.

### Status-tag tones

Every status maps to one tone in [`src/lib/status.ts`](../../client/src/lib/status.ts); labels are in [`src/i18n/en/status.json`](../../client/src/i18n/en/status.json). Staff see a privilege's or license's computed status, such as "Encumbered"; PAs and the public see the Active/Inactive pill.

| Tone | For | Background | Text | Grade difference |
|---|---|---|---|---|
| `success` | in good standing, or granted | `success-lighter` | `success-darker` | 55 |
| `info` | with staff | `info-lighter` | `info-darker` | 55 |
| `warning` | waiting on the PA | `warning-lighter` | `ink` | 85 |
| `error` | refused, withdrawn or terminated by a decision, or under discipline | `error-lighter` | `error-darker` | 60 |
| `neutral` | closed, or not in force for any other reason | `base-lighter` | `base-darkest` | 80 |

A grade difference of 50 or more passes WCAG AA for text ([USWDS color](https://designsystem.digital.gov/design-tokens/color/overview/)). `warning-darker` on `warning-lighter` is only 45, hence `ink`. If a brand changes a state family, keep each pair at 50 or more. The label carries the meaning, never the colour alone.

[`src/styles/status-tag.scss`](../../client/src/styles/status-tag.scss) holds the tones as a Sass map and emits one `.status-tag--{tone}` class per tone.

## Type

Public Sans for every role, Q-09's default.

| What | Tokens | Setting |
|---|---|---|
| Families | `sans` (Public Sans), `mono` (Roboto Mono) | `$theme-font-type-sans`, `$theme-font-type-mono` |
| Roles | `ui`, `body`, `heading` use `sans`; `code` uses `mono` | `$theme-font-role-*`; `heading` changes from USWDS's `serif` |
| Scale | `3xs`, `2xs`, `xs`, `sm`, `md`, `lg`, `xl`, `2xl`, `3xl` | `$theme-type-scale-*` |
| Headings | `h1` `2xl`, `h2` `xl`, `h3` `lg`, `h4` `sm`, `h5` `xs`, `h6` `3xs` | `$theme-h{n}-font-size` |
| Weights | `normal` (400), `semibold` (600), `bold` (700) | `$theme-font-weight-*`; `semibold` is off in USWDS and turned on |
| Line height | `1` to `6`; body `5` | `$theme-body-line-height` |

## Spacing

| What | Tokens | Setting |
|---|---|---|
| Units | `0`, `05`, `1`, `105`, `2`, `205`, `3`, `4`, `5`, `6`, `8`, `10` | fixed USWDS scale, 8px per unit |
| Page gutters | mobile `2`, desktop `4` | `$theme-site-margins-mobile-width`, `$theme-site-margins-width` |
| Grid gap | mobile `2`, desktop `4` | `$theme-column-gap-mobile`, `$theme-column-gap-desktop` |
| Field width | `mobile-lg` | `units("mobile-lg")` |

## Radius

`0`, `sm`, `md`, `lg`, `pill`, set through `$theme-border-radius-sm`, `-md`, and `-lg`.
