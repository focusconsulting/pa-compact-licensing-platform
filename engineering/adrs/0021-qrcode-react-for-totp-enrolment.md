---
category: architecture
status: proposed
date: 2026-11-17
---

# ADR-0021: qrcode.react for TOTP Enrolment

## Status

Proposed

## Date

2026-11-17

## Context

SCRUM-104 requires TOTP at every sign-in (F-04, D4). A user without an
authenticator app enrols at their first sign-in: Cognito returns a
secret, and the user adds it to an app on their phone. Staff sign in on
desktop machines, so the secret has to cross from the screen to the
phone. Typing the 32-character base32 key by hand is slow and
error-prone; authenticator apps expect to scan the `otpauth://` URI as a
QR code. Nothing in the client's dependencies draws one.

## Decision

The login page renders the enrolment URI with `QRCodeSVG` from
[qrcode.react](https://github.com/zpao/qrcode.react). The setup key and
an `otpauth://` link stay beside it, for screen-reader users and for
enrolling on the same device.

The QR code is drawn in the browser. The secret is never sent to a
third-party service.

## Pros and cons

### qrcode.react (chosen)

- Pro: a React component that renders SVG, with no dependencies of its
  own and only React as a peer.
- Pro: widely used (about 15 million weekly downloads), ISC-licensed,
  latest release (4.2.0) from December 2024.
- Con: one more package to keep current, and to name for the
  Commission's consent (SOW §7.5).

### qrcode

- Pro: the most used QR library.
- Con: brings in `yargs` and `pngjs` for its command-line and PNG
  output, neither of which the client needs.

### No QR code

- Pro: no dependency.
- Con: every enrolling user types the key, which is the main source of
  failed TOTP setups.

### Render the QR code on a server or external service

- Con: sends the TOTP secret off the page. That is unacceptable for a
  second factor.

## Consequences

- `qrcode.react` is a client dependency, listed in the client README.
- The PR that adds it names it for the Commission's written consent.

## Related

- Constitution Principle I (new dependencies need an ADR) and the
  dependencies-and-licenses rule (SOW §7.5).
- [ADR-0010](0010-local-sign-in-uses-password-auth.md): the local sign-in
  path these steps share.
- SCRUM-104.
