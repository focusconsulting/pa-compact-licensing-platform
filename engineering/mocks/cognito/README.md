# Cognito mock

[cognito-local](https://github.com/jagregory/cognito-local) with the local
user pool, so the app signs in with no AWS account. It is local tooling and is
never deployed.

cognito-local has no SRP, so locally the client signs in with
`USER_PASSWORD_AUTH`, set by `NEXT_PUBLIC_COGNITO_AUTH_FLOW` in
`engineering/client/.env`. Deployed clients leave it unset and use SRP, the
only flow the deployed app client allows
([ADR-0010](../../adrs/0010-local-sign-in-uses-password-auth.md)).

## Users

[`db/local_licensing.json`](db/local_licensing.json) holds the local users,
matching [`engineering/api/seed/users.sql`](../../api/seed/users.sql).
Everyone signs in with `Local-Passw0rd!`, except `backfill@example.com`, which
starts in `FORCE_CHANGE_PASSWORD` with `Temp-Passw0rd!` to exercise the first
sign-in. Changes such as a new password last until the container is recreated.
