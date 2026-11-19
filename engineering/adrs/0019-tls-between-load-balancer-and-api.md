---
category: architecture
status: proposed
date: 2026-11-12
---

# ADR-0019: TLS Between the Load Balancer and the API

## Status

Proposed

## Date

2026-11-12

## Context

The constitution requires TLS on every hop, including the load balancer
to the API ([Principle VII](../engineering-constitution.md#vii-zero-trust)),
and SCRUM-84's acceptance criteria say no connection between components
uses plain HTTP. The API container served plain HTTP on port 8000.
Plan: [Harden the infrastructure](../thoughts/shared/plans/iac/2026-11-12-SCRUM-84-harden-infrastructure.md).

An Application Load Balancer encrypts its connection to an HTTPS target
but does not validate the target's certificate: a self-signed or expired
one is accepted
([AWS](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-target-groups.html)).
Whatever certificate the container presents, this hop gains encryption
and no verification of the API's identity.

An ACM certificate's private key cannot leave ACM unless the certificate
was issued as exportable, so the certificate CloudFront and the load
balancer present cannot be loaded into the container as it stands.

## Decision

1. **The API container serves TLS with a certificate it generates at
   start.** [`licensing_api/serve.py`](../api/licensing_api/serve.py)
   writes a new EC P-256 key and a self-signed certificate for
   `localhost`, then replaces itself with gunicorn bound to them. It is
   the production image's command. The target group and its health check
   speak HTTPS, and the container's own health check trusts exactly the
   generated certificate.
2. **`cryptography` is imported directly** to build the certificate. It
   is already installed through `pyjwt[crypto]`
   ([ADR-0018](0018-pyjwt-for-cognito-token-verification.md)) and is now
   declared in `pyproject.toml`.
3. **Local development is unchanged.** `just dev` runs uvicorn over HTTP;
   only the deployed image's command adds TLS, so no setting switches it.
4. **Production moves to one CA-issued certificate on every hop**
   ([SCRUM-192](https://focusdigital.atlassian.net/browse/SCRUM-192)).
   This decision stands until then.

## Pros and cons

### A certificate generated at start (chosen)

- Pro: the hop is encrypted with nothing to store, deliver, or rotate. A
  key exists in one task and is gone when the task stops.
- Pro: no cost and no new package.
- Pro: each task has its own key, so one leaked key exposes one task.
- Con: nothing verifies the API's identity on this hop. An attacker would
  need to intercept traffic inside the VPC, which AWS authenticates at
  the packet level.
- Con: an auditor sees a self-signed certificate and needs this record.

### An exportable ACM public certificate

- Pro: the same certificate on every hop, which is the preference for
  production.
- Con: about $79 per wildcard name per 198-day issuance, and the private
  key must be stored in Secrets Manager, delivered to every task, and
  replaced on each renewal.
- Con: every task holds the same key.
- Con: the load balancer still validates nothing, so the gain is
  consistency, not verification.

### AWS Private CA

- Pro: certificates issued per task by a CA we control.
- Con: about $400 a month per CA ($50 in short-lived mode), and a CA to
  operate, for a hop whose client ignores the issuer.

### A TLS sidecar (Envoy or nginx)

- Pro: the API image is untouched.
- Con: another container to run, patch, scan, and draw, and it still
  needs a certificate from one of the options above.

### Plain HTTP with an exception

- Con: fails the acceptance criterion and the constitution without need.

## Consequences

- The production image's command is `python -m licensing_api.serve`.
  Plain HTTP on port 8000 no longer answers in a deployed container.
- Scaled tasks present different certificates. Nothing compares them:
  the load balancer connects to each target separately, and no other
  client reaches the container.
- Anything that later calls the API directly inside the VPC, or mutual
  TLS, would need a certificate it can verify; that is SCRUM-192's
  ground.
- The ASVS mapping (SCRUM-84, Phase 6) cites this ADR for the hop.
