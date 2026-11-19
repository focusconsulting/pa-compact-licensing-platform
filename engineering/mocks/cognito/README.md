# Cognito mock

[cognito-local](https://github.com/jagregory/cognito-local) with the local
user pool, so the app signs in with no AWS account. It is local tooling and is
never deployed.

cognito-local has no SRP, so locally the client signs in with
`USER_PASSWORD_AUTH`, set by `NEXT_PUBLIC_COGNITO_AUTH_FLOW` in
`engineering/client/.env`. Deployed clients leave it unset and use SRP, the
only flow the deployed app client allows
([ADR-0010](../../adrs/0010-local-sign-in-uses-password-auth.md)).

The local pool requires no TOTP, because cognito-local cannot enrol an
authenticator app at sign-in. To try SRP and TOTP, run `just up dev`
from the repository root, which signs in with DEV's pool instead
([ADR-0022](../../adrs/0022-local-totp-against-the-dev-pool.md)).

## Users

[`db/local_licensing.json`](db/local_licensing.json) holds the local users,
matching [`engineering/api/seed/users.sql`](../../api/seed/users.sql).
Everyone signs in with `Local-Passw0rd!`, except `backfill@example.com`, which
starts in `FORCE_CHANGE_PASSWORD` with `Temp-Passw0rd!` to exercise the first
sign-in. Changes such as a new password last until the container is recreated.

With `NEXT_PUBLIC_DEV_SIGN_IN_PASSWORD` set, as
[`engineering/client/.env.example`](../../client/.env.example) sets it, the
sign-in page lists these users and signs in as the one you choose
([ADR-0020](../../adrs/0020-development-only-sign-in-list.md)). The list is
read from this mock, so a user added here appears in it.
