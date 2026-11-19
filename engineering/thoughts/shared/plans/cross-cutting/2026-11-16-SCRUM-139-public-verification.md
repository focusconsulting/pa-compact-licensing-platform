# Public Privilege Verification Implementation Plan

## Overview

Let anyone, signed in or not, confirm that a PA holds a compact privilege: a `/verify` page backed by two unauthenticated routes under `/api/public/`. The response is an allow-list, the web firewall answers a caller who exceeds the rate limit with `429`, and a page URL loaded directly resolves.

## Related

- **Spec**: epic 11 in [MVP epics and tickets](../../../../../product/backlog/mvp-jira-tickets.md) and V-01 in the [MVP ticket breakdown](../../../../../product/backlog/mvp-ticket-breakdown.md)
- **Flows**: [FLOW-08](../../../../../product/context/flows/08-public-verification.md) (the flow and its wireframes), [FLOW-05](../../../../../product/context/flows/05-adverse-action-cascade.md) (what the public view withholds), [FLOW-06](../../../../../product/context/flows/06-state-machines.md) (the public status vocabulary)
- **Compact rules**: [Rule 4 §4.5(b)–(d)](../../../../../product/context/research-corpus/sources/rule-4-compact-data-system--confidentiality-information-sharing.md); SOW §2.1 (v2: "verify active and inactive PA compact privileges")
- **Decisions**: D1 (privilege status is computed). Q-12, closed in this plan's session on 2026-11-16 (Michael Kalish):
  - The allow-list is the Q-12 default: first name, last name, suffix, state of qualifying license, and per privilege its state, number, status, issue date, and expiry date. No NPI, no middle name, no deactivation reason, no adverse-action data. This plan absorbs the contract step, SCRUM-138.
  - The public sees three statuses: `active`, `expired`, `inactive`. An encumbered privilege shows as `inactive`, whether or not the action behind it is public, so nothing tells a sealed action from any other deactivation.
  - The branch stacks on the SCRUM-84 stack (PR #224), which holds the web firewall.
  - This ticket fixes direct page loads on CloudFront, which return `403` today for every page but `/`.
  - `/` becomes the public front door and the dashboard moves to `/dashboard`. The front door is the board's V0 ([`5126:16369`](https://www.figma.com/design/k1W9PxXhtQ3fopcKUePpH9/PA-Compact-Parts-Library?node-id=5126-16369)), the designed version of A2: three cards, with the search on its own page, and V0s for a signed-in visitor. This replaces the two columns first decided here.
  - The pages follow block V on the board ([`5121:15647`](https://www.figma.com/design/k1W9PxXhtQ3fopcKUePpH9/PA-Compact-Parts-Library?node-id=5121-15647)), drawn by the product step, SCRUM-137.
  - A cache or read replica for the public queries is deferred to SCRUM-202.
  - `StateRef` stays as planned here and is reconciled with the application stack's `StateOut` when that stack merges.
- Jira: SCRUM-139, under SCRUM-98. Absorbs SCRUM-138. Blocked by SCRUM-84 (in review). Blocks SCRUM-142. Follow-up: SCRUM-202 (read replica).
- ADRs: [ADR-0009](../../../../adrs/0009-route-authorization-and-change-context.md) (`public()`), [ADR-0013](../../../../adrs/0013-generated-api-client-and-mocks.md) (generated client), [ADR-0006](../../../../adrs/0006-reference-time-zone-and-dates.md) (dates), [ADR-0015](../../../../adrs/0015-opentofu-for-infrastructure.md). No new ADR: no dependency, pattern, or exception is introduced.
- **Area**: cross-cutting (api, client, iac)

## Constitution Check

- **I, Idiomatic Python.** One `routes/public_verification.py` and one `repo/public_verification.py`; ORM queries only; every route sets `name` and `description` and returns a Pydantic model.
- **II, The API is the only authority.** The API computes the public status and applies the allow-list. The client maps nothing: it shows the status and dates it is given.
- **III, Test coverage.** 100% line and branch on the new API and client code; API tests go through the endpoint against Postgres.
- **IV, No mock code.** The `429` body is sent by the firewall in AWS. The API documents it and never fakes it; locally there is no rate limit.
- **V, E2E and accessibility.** One Playwright spec covers search, results, and detail, with an empty-result error path, and scans every page. `/verify` pages join the pa11y scan.
- **VI, The record is the audit trail.** Read-only: no writes, events, or history. No audit-log entry, since the audit log records staff reads of private data and this returns public data only.
- **VII, Zero trust.** Query parameters are validated and unknown ones rejected; the response models forbid extra fields. No secret is added.
- **VIII, Observability.** Each search logs its mode and result count, never its terms. The firewall's rate rules already have metrics and an alarm (SCRUM-84).
- **IX, Links.** This plan links the spec and flows; the code cites Rule 4 §4.5 once, on the response models.
- **X, USWDS.** The pages compose existing components (`PrivilegeCard`, `DataTable`, `TextField`, `EmptyState`) in the layouts the Parts Library draws; every string goes through `i18next`; each new component and page has a story.
- **XI, Prose.** FLOW-08 is the feature's one home; other docs link to it. A second document under `engineering/docs/` repeated it and was removed in review.
- **XII, Fresh clone.** No new tool or setting. `engineering/docs/demo.md` gains the verification step.
- **XIII, Dates.** See [Dates and Deadlines](#dates-and-deadlines).
- **XIV, Migrations.** None.
- **XV, Reviewable PRs.** Four stacked pull requests, each under 600 hand-written production lines.

## Current State Analysis

- **The data is there.** `privileges`, `practitioners`, `qualifying_licenses`, and `adverse_actions` (with `is_public`) exist, with `v_privilege_status` computing `active | expired | encumbered | inactive` (`engineering/api/licensing_api/repo/status.py:61-88`, `150-170`). The demo seed has one privilege in each status (`engineering/docs/demo.md:37-51`).
- **The namespace is reserved and empty.** `'/public': []` in `engineering/api/licensing_api/routes/__init__.py:19`; `tests/test_route_access.py:21` already requires every route under it to be `public()`. The prefix is `/api/public/`: there is no `/v1`, and the firewall rule matches `/api/public/` (`waf.tf:12`). The ticket's `/api/v1/public/*` is a slip.
- **Nothing reads a privilege yet.** No route or query function returns practitioners, licenses, or privileges.
- **The computed status would leak.** `privilege_status_query` marks a privilege `encumbered` for any in-force action, ignoring `is_public` (`status.py:106-115`, `161-164`), and `PrivilegeStatus.status_reason` carries the deactivation reason.
- **Name search is half-indexed.** Only `lower(legal_last_name)` is indexed (`db-migrations/20261007_100000_data_model_core_entities_a.sql:151`). That is enough for an exact match on both names.
- **The client has two pages**, `/` and `/login`. A page is public by not wrapping itself in `ProtectedRoute` (`engineering/client/src/app/login/page.tsx`). The typed client throws without a session (`engineering/client/src/lib/api.ts:9-22`). Signed out, the header shows only the wordmark (`AppShell.tsx:68-74`).
- **Direct page loads fail in AWS.** The export writes `login.html`; CloudFront has no rewrite, and S3 answers a missing key with `403`, which the `404` fallback (`cdn.tf:247-252`) never sees. Measured on staging on 2026-11-16: `/login` → `403`, `/login.html` → `200`. Locally and in E2E, `serve` resolves clean URLs, so nothing catches it.
- **The firewall blocks with `403`.** Both CloudFront rate rules use `block {}` (`waf.tf:53-55`): 300 requests per five minutes per IP on `/api/public/`, 2,000 on `/api/`.
- **E2E in CI seeds users only** (`.github/workflows/e2e.yml:55`), so no privilege exists to verify.

## Desired End State

A member of the public opens the site, or `/verify` directly, searches by first and last name or by privilege number, sees who matches, and opens one person's page listing each privilege with its state, number, status, and dates. Nothing else about the PA is reachable without signing in. A caller over the limit gets `429` with the API's error shape. `https://<site>/verify` and `/login` load directly.

Verified by: the API and client test suites at 100% coverage, the Playwright spec, the pa11y scan, and on staging a direct load of `/verify` and a burst of requests ending in `429`.

### Key Discoveries

- `public()` at router level is the whole opt-out from authentication (`engineering/api/licensing_api/routes/health.py:15`).
- `Data[T]`, `Paged[T]`, `page_query`, and `example()` are the response conventions (`engineering/api/licensing_api/responses.py`); `tests/test_openapi.py` requires an example on every success model and that `openapi.json` matches the code.
- `PrivilegeCard` already takes a status and an expiry and renders FLOW-06's qualifier (`engineering/client/src/components/PrivilegeCard.tsx:42-51`); its `inactive` qualifier is "Deactivated".
- The client has no table of state names on this base, so the API returns each state as a `StateRef`: its code and name.
- A static export cannot have `/verify/[id]`, so the detail page takes its id from the query string.
- The CloudFront web ACL includes `AWSManagedRulesAnonymousIpList`, and the distribution is US-only (Q-28). A visitor on a VPN or abroad is blocked before any of this runs. That is existing policy, not changed here.

## What We're NOT Doing

- No NPI, middle name, other names, date of birth, address, eligibility, or license status and number in any response.
- No discipline status, discipline dates, or history timeline, though CompactConnect shows them (crosswalk §6).
- No partial, prefix, phonetic, or accent-insensitive name matching, and no search by state alone.
- No rate limiting in the API and no CAPTCHA.
- No cache and no read replica for the public queries (deferred to SCRUM-202). The constitution allows a cache only with an ADR showing a measured need, and there is no traffic to measure yet. See [Performance Considerations](#performance-considerations) for the two options and when to take one.
- No registration door on the home page; it arrives with PA registration.
- No not-found page for unknown URLs (SCRUM-194).
- No change to `v_privilege_status` or to what staff and PAs see.

## Implementation Approach

Four pull requests, stacked in this order: the API and the contract, the `/verify` pages and their E2E spec, the front door and the dashboard's move, then the infrastructure. Each merges on its own; verification works locally after the second, and in AWS after the fourth. Phases 2 and 3 were rewritten on 2026-11-16 from FLOW-08 and block V, the output of the product step SCRUM-137, and swapped so the front door never links to a page that isn't there.

The allow-list is the response models: they forbid extras and are built field by field. Two tests hold it there: one pins each model's field set to the documented list, and one fills every private column with a marker value and asserts no marker reaches a response. The queries return ordinary rows, as every repo module does; an earlier draft selected only the allow-listed columns, which review judged a second mechanism for what the models already do.

## Phase 1: The API and the allow-list contract

### Overview

`GET /api/public/privilege-holders` and `GET /api/public/privilege-holders/{id}`, with the allow-list committed as schema and documentation. Closes SCRUM-138.

### Changes Required

#### 1. Public status

**File**: `engineering/api/licensing_api/repo/status.py`
**Changes**: Add the public vocabulary and the mapping from the computed status. The mapping is total over `PrivilegeComputedStatus`, so a new computed status fails type checking until it is given a public one.

```python
class PublicPrivilegeStatus(StrEnum):
    """What public verification shows (FLOW-06). An encumbered privilege is ``inactive``: the public
    never learns that an adverse action exists, public or not (Rule 4 §4.5(c))."""

    ACTIVE = 'active'
    EXPIRED = 'expired'
    INACTIVE = 'inactive'


PUBLIC_STATUS: Mapping[PrivilegeComputedStatus, PublicPrivilegeStatus] = {
    PrivilegeComputedStatus.ACTIVE: PublicPrivilegeStatus.ACTIVE,
    PrivilegeComputedStatus.EXPIRED: PublicPrivilegeStatus.EXPIRED,
    PrivilegeComputedStatus.ENCUMBERED: PublicPrivilegeStatus.INACTIVE,
    PrivilegeComputedStatus.INACTIVE: PublicPrivilegeStatus.INACTIVE,
}
```

Add `PublicPrivilegeStatus` to `STATUS_ENUMS` in `engineering/api/scripts/export_openapi.py`.

#### 2. Queries

**File**: `engineering/api/licensing_api/repo/public_verification.py` (new)
**Changes**: Ordinary queries that return rows.

- `holders()`: practitioners who hold at least one privilege (`exists()` on `privileges`) and have a name and a state of qualifying license. `holders_by_name` and `holders_by_privilege_number` narrow it; names match on `func.lower(column) == value.lower()` after trimming, so the existing `lower(legal_last_name)` index serves it. `get_holder` finds one by `public_id`.
- `privilege_states(session, practitioners)`: for a page of results, the states each holds a privilege in. One light query for the page; the status view is not read for a search.
- `privileges_of(session, practitioner)`: one PA's privileges, each with its status from `PrivilegeStatus`.
- `state_names(session)`: each state's name by code.

The state of qualifying license is `practitioners.current_sql_state_code`.

#### 3. Routes and response models

**File**: `engineering/api/licensing_api/routes/public_verification.py` (new)
**Changes**:

```python
router = APIRouter(
    prefix='/privilege-holders',
    dependencies=[public()],
    # The web firewall answers for the API past the rate limit (waf.tf).
    responses={429: {'model': ErrorResponse}},
)


class StateRef(BaseModel):
    """A state by code and name, for a response that names a state without describing it."""

    model_config = ConfigDict(extra='forbid', json_schema_extra=example(code='OK', name='Oklahoma'))
    code: str
    name: str


_KANSAS = StateRef(code='KS', name='Kansas')
_OKLAHOMA = StateRef(code='OK', name='Oklahoma')


class PublicPrivilege(BaseModel):
    """A privilege as the public sees it. The allow-list is closed (Rule 4 §4.5(b)–(d), Q-12):
    a field is added here only by changing FLOW-08."""

    model_config = ConfigDict(
        extra='forbid',
        json_schema_extra=example(
            state=_OKLAHOMA,
            number='PA-OK-000123',
            status=PublicPrivilegeStatus.ACTIVE,
            issued_on=date(2026, 11, 2),
            expires_on=date(2027, 12, 31),
        ),
    )
    state: StateRef
    number: str
    status: PublicPrivilegeStatus
    issued_on: date
    expires_on: date


_PRIVILEGE = PublicPrivilege(
    state=_OKLAHOMA,
    number='PA-OK-000123',
    status=PublicPrivilegeStatus.ACTIVE,
    issued_on=date(2026, 11, 2),
    expires_on=date(2027, 12, 31),
)
_HOLDER = {
    'id': UUID('5f0c2d6e-8a41-4b7c-9d13-6e2f4a8b1c90'),
    'first_name': 'Pat',
    'last_name': 'Morgan',
    'name_suffix': None,
    'state_of_qualifying_license': _KANSAS,
}


class PrivilegeHolderSummary(BaseModel):
    model_config = ConfigDict(
        extra='forbid', json_schema_extra=example(**_HOLDER, privilege_states=[_OKLAHOMA])
    )
    id: UUID
    first_name: str
    last_name: str
    name_suffix: str | None
    state_of_qualifying_license: StateRef
    privilege_states: list[StateRef]


class PrivilegeHolder(BaseModel):
    model_config = ConfigDict(extra='forbid', json_schema_extra=example(**_HOLDER, privileges=[_PRIVILEGE]))
    id: UUID
    first_name: str
    last_name: str
    name_suffix: str | None
    state_of_qualifying_license: StateRef
    privileges: list[PublicPrivilege]
```

Every example is a module-level constant. A nested value is an instance of its own model (`_OKLAHOMA`, `_PRIVILEGE`), so an example that drifts from a nested model fails at import and not only when the OpenAPI document is built; the shared holder fields are a dict, after `_DOCUMENT_EXAMPLE` in `routes/document.py:53`. `PublicPrivilege`'s own example repeats `_PRIVILEGE`'s values in the implementation by building both from one `_PRIVILEGE_FIELDS` dict.

`StateRef` is the code-and-name pair. The application stack's `StateOut` in `routes/catalogue.py` (PR #208, unmerged, not on this base) is that pair plus `is_member` and `is_live`, which a verification response has no reason to carry. Whichever stack merges second makes `StateOut` extend `StateRef`, so the two fields have one definition.

- `GET ''` → `Paged[PrivilegeHolderSummary]`. Query parameters `first_name`, `last_name` (each 1–100 characters after trimming) and `privilege_number` (pattern `^[Pp][Aa]-[A-Za-z]{2}-\d{6,}$`, upper-cased before the lookup). Exactly one mode: both names, or the number alone. Anything else is `AppError(422, ErrorCode.ValidationError, ...)`. Paged with `page_query('last_name', 'first_name', default_sort='last_name,first_name')`, tie-broken on the holder's id. No match is `200` with an empty list.
- `GET '/{holder_id}'` → `Data[PrivilegeHolder]`. `holder_id` is the practitioner's `public_id`. An unknown id, or a practitioner with no privilege, is `AppError(404, ErrorCode.NotFound, ['No such privilege holder'])`, one message for both.
- `issued_on` is `compact_date_at(issued_at, await reference_time_zone(session))`.
- Each search logs `logger.info('public verification search', extra={'mode': ..., 'results': total})`.
- Reject unknown query parameters with a dependency that compares `request.query_params` to the allowed set, so a typo is a `422` and not a silently ignored filter.

**File**: `engineering/api/licensing_api/routes/__init__.py`
**Changes**: `'/public': [public_verification.router]`.

**File**: `engineering/api/licensing_api/errors.py`
**Changes**: Add `RateLimited = 'RATE_LIMITED'` to `ErrorCode`, with a comment that the web firewall sends it and the API never raises it.

#### 4. Generated

`cd engineering/api && just openapi` rewrites `engineering/api/openapi.json`.

#### 5. Documentation

- FLOW-08 holds the contract SCRUM-138 asked for: the allow-list and why each field is public, the search rules, the three statuses, and what is withheld.
- `engineering/docs/data-model.md`: the Public tier row links to it.
- `engineering/docs/roles-and-permissions.md`: the `/public` row links to it.
- `product/context/flows/06-state-machines.md`: one sentence, that the public sees `active`, `expired`, and `inactive`, and an encumbered privilege shows as `inactive`.
- `product/backlog/mvp-ticket-breakdown.md`: Q-12's row records the answer and the date.

### Success Criteria

#### Automated Verification

- [x] Local services running: `cd engineering/api && just infra`
- [x] Tests pass at 100% line and branch coverage: `cd engineering/api && just test-coverage`
- [x] Lint, format, and type checks pass: `cd engineering/api && just lint`
- [x] `openapi.json` matches the code (`tests/test_openapi.py`)
- [x] Route access rules hold (`tests/test_route_access.py`)
- [x] Markdown lint passes: `pre-commit run --files <changed .md files>`

#### Manual Verification

- [ ] After `just seed demo`, `curl 'localhost:8000/api/public/privilege-holders?first_name=lex&last_name=license-action'` returns Lex with no `Authorization` header, and his detail shows `inactive` with no reason
- [ ] The same call with only `last_name` is a `422`

**Implementation Note**: After this phase's automated checks pass, pause for manual confirmation before Phase 2.

---

## Phase 2: The `/verify` pages and the E2E spec

### Overview

The search, its results, and a PA's page, from FLOW-08's frames V1 to V3i. Built before the front door so that the front door's third card never links to a page that isn't there.

### Changes Required

#### 1. An unauthenticated client

- `engineering/client/src/lib/api.ts`: export `publicApi`, the same `createClient<paths>` without the `authorize` middleware.
- `engineering/client/src/lib/verification.ts` (new): the two calls, the `Search` type (both names, or a number), and the helpers that read a search from an address and write it back.
- `cd engineering/client && pnpm generate` rewrites `src/api/schema.d.ts`.

#### 2. Search and results

- `src/components/VerifySearchForm.tsx` (V1, V1n): a radio pair picks the search; `react-hook-form` with `TextField`s. The browser's `required` and `pattern` stop an empty or malformed search.
- `src/components/VerifyResults.tsx` (V2, V2e): "Results (n)", a `DataTable` whose first column links to the PA, `EmptyState` when no one matches, and USWDS `Pagination` past one page.
- `src/app/verify/page.tsx`: the form above its results. The search lives in the address (`?first_name=&last_name=` or `?privilege_number=`, and `page`), read with `useSearchParams` inside the `Suspense` boundary a static export needs, so results survive a reload and Back. A `429` shows the warning alert of V2x and keeps the search.

#### 3. A PA's page

- `src/app/verify/practitioner/page.tsx` (V3, V3i): reads `?id=`, shows the name, the state of qualifying license, and one `PrivilegeCard` per privilege. A static export cannot have `/verify/[id]`.
- The result's link carries the search, so "Back to results" is a real link and survives a reload; opened from a bare link, it reads "Look up another PA".
- `src/components/PrivilegeCard.tsx`: `inactiveQualifier={false}` drops "Deactivated" from an inactive card (Q-31's default). The card's own tag and labels stand: an expired privilege reads "Inactive" with "Expired: date" beside it, and the labels are "Active from" and "Privilege number", where V3i draws an "Expired" tag and "Issued".
- An unknown or malformed id, or none, shows "We couldn't find that PA".

#### 4. Strings, stories, scans, docs

- `src/i18n/en/verify.json`, registered in `src/i18n/config.ts` and `src/@types/resources.ts`.
- Stories for both components and both pages, and a public inactive `PrivilegeCard`.
- `.pa11yci.json`: `/verify/`, `/verify/` with a search, and `/verify/practitioner/`.
- `engineering/docs/design/wireframe-kit.md` (a "Lookup" template), `demo.md` (the sprint-review step).

#### 5. E2E

`engineering/e2e/tests/public-verification.spec.ts`: signed out throughout, against the demo seed CI already loads. By name and back to the results; by number; expired; inactive with no reason for a license action and for a privilege action; no match; a PA with no privilege; an unknown address.

### Success Criteria

#### Automated Verification

- [x] Tests pass at 100% coverage: `cd engineering/client && pnpm test:coverage`
- [x] Type checking passes: `cd engineering/client && pnpm exec tsc --noEmit`
- [x] Linting passes: `cd engineering/client && pnpm lint`
- [x] Build succeeds and writes `out/verify.html` and `out/verify/practitioner.html`: `cd engineering/client && pnpm build`
- [x] pa11y is clean: `cd engineering/client && pnpm a11y`
- [x] The verification spec passes against the demo seed: `cd engineering/e2e && pnpm exec playwright test public-verification`
- [x] E2E type check passes: `cd engineering/e2e && pnpm typecheck`

#### Manual Verification

- [ ] Signed out, `/verify` finds Avery Active by name and by number; Back from the PA's page keeps the results
- [ ] Pia Expired shows "Expired:" with the date in red; Lex and Enzo show "Inactive" and nothing about why
- [ ] Side by side with V1 to V3i, the pages read as the same product
- [ ] Keyboard only: switch the search, search, open a result, return
- [ ] The pages read correctly at 320px wide

---

## Phase 3: The front door, and the dashboard at `/dashboard`

### Overview

`/` stops being a page that sends a visitor to sign in. It becomes the front door, V0 ([`5126:16369`](https://www.figma.com/design/k1W9PxXhtQ3fopcKUePpH9/PA-Compact-Parts-Library?node-id=5126-16369)) and V0s ([`5126:16573`](https://www.figma.com/design/k1W9PxXhtQ3fopcKUePpH9/PA-Compact-Parts-Library?node-id=5126-16573)), and the dashboard gets its own address.

One address per meaning is the reason for the move rather than showing either page at `/` by session. A page that is public sometimes cannot be drawn until the session check finishes, so every visitor would wait on it; `ProtectedRoute` would no longer describe the whole page; and titles, bookmarks, the pa11y scan, and E2E would each have two pages behind one address.

### Changes Required

#### 1. Move the dashboard

- `git mv` `src/app/page.tsx`, `page.test.tsx`, `PaDashboard.tsx`, and `PaDashboard.test.tsx` to `src/app/dashboard/`, with a `layout.tsx` for its title. Rename `src/stories/pages/home.stories.tsx` to `dashboard.stories.tsx`.
- `src/app/login/page.tsx`: after sign-in, go to `/dashboard`. `src/app/application/page.tsx` leaves the wizard for `/dashboard`.
- `src/lib/navigation.ts`: the three portal home items point to `/dashboard`, and `AppShell` no longer treats `/` as a nav item.
- `ProtectedRoute` still sends a signed-out visitor to `/login`. The wordmark still links to `/`.

#### 2. The front door

**File**: `src/app/page.tsx` (new)
**Changes**: `PageHeading` with the intro, then a USWDS `CardGroup` of three `Card`s, each a heading, one line, and a link styled as a button. The cards stack below desktop width.

- Physician assistants, and State and Commission staff: each links to `/login`, as "Sign in as a PA" and "Sign in as staff", so the two links are told apart by name. Once the session check finds a signed-in visitor, their own portal's card reads "Go to your dashboard" and links there; until then it is the sign-in card, so nothing waits on the check.
- Look up a Compact Privilege: links to `/verify`.
- V0's first button reads "Sign in or create an account". Creating an account waits for PA registration (epic 5), which gives it somewhere to send people.

#### 3. Strings, stories, scans, docs

- `src/i18n/en/home.json`, registered as above.
- `src/stories/pages/home.stories.tsx` for the new page.
- `.pa11yci.json`: add `/`.
- `engineering/e2e/tests/sign-in.spec.ts`: a signed-in user lands on `/dashboard`. `public-verification.spec.ts` starts from `/` and follows the third card. `pa-dashboard.spec.ts` expects `/dashboard`.
- `engineering/docs/design/wireframe-kit.md`: a "Front door" template.

### Success Criteria

#### Automated Verification

- [x] Tests pass at 100% coverage: `cd engineering/client && pnpm test:coverage`
- [x] Type checking passes: `cd engineering/client && pnpm exec tsc --noEmit`
- [x] Linting passes: `cd engineering/client && pnpm lint`
- [x] Build succeeds and writes `out/index.html` and `out/dashboard.html`: `cd engineering/client && pnpm build`
- [x] pa11y is clean: `cd engineering/client && pnpm a11y`
- [ ] E2E passes: `just e2e` (run locally on 2026-11-16 for the sign-in, dashboard, and verification specs only; CI runs all of them on a fresh seed)

#### Manual Verification

- [ ] Signed out, `/` shows all three cards at once, with no flash of an empty page
- [ ] Signing in lands on `/dashboard`; `/dashboard` signed out goes to `/login`
- [ ] Signed in, `/` offers the dashboard on the visitor's own card, and every nav item still works
- [ ] At 320px wide the cards stack: PAs, staff, lookup

**Implementation Note**: After this phase's automated checks pass, pause for manual confirmation before Phase 4.

---

## Phase 4: `429` at the firewall, and direct page loads

### Overview

Two changes to the CloudFront distribution, applied to staging.

### Changes Required

#### 1. Rate-limited requests get `429`

**File**: `engineering/infrastructure/iac/components/app/opentofu/waf.tf`
**Changes**: On `aws_wafv2_web_acl.cloudfront`, both rate rules answer with the API's error shape. The Cognito web ACL is unchanged: Cognito's SDK reads its own errors.

```hcl
custom_response_body {
  key          = "rate-limited"
  content_type = "APPLICATION_JSON"
  # The API's ErrorResponse (errors.py), which the client reads on every other error.
  content = jsonencode({ code = "RATE_LIMITED", details = ["Too many requests. Try again in a few minutes."] })
}

# in each rate rule
action {
  block {
    custom_response {
      response_code            = 429
      custom_response_body_key = "rate-limited"
      response_header {
        name  = "Retry-After"
        value = "300"
      }
    }
  }
}
```

The public limit stays at 300 per five minutes per IP: a lookup is two requests, so one address gets 150 lookups in five minutes. Replace the "SCRUM-139 tunes the public limit" comment with that reasoning.

#### 2. Page URLs resolve to their `.html` file

**File**: `engineering/infrastructure/iac/components/app/opentofu/cdn.tf`
**Changes**: A second CloudFront function, on viewer-request of the default behaviour only, so `/api/*` is untouched.

```hcl
resource "aws_cloudfront_function" "page_html" {
  name    = "${var.environment_name}-${local.application_name}-page-html"
  runtime = "cloudfront-js-2.0"
  publish = true
  # The static export writes /verify as verify.html, and S3 has no key named "verify".
  code = <<-EOF
    function handler(event) {
      var request = event.request;
      var uri = request.uri.replace(/\/+$/, "");
      if (uri !== "" && uri.split("/").pop().indexOf(".") === -1) {
        request.uri = uri + ".html";
      }
      return request;
    }
  EOF
}
```

`/` still resolves through `default_root_object`; `/_next/static/…` and other files keep their extension and pass through.

#### 3. Documentation

- `engineering/docs/security/infrastructure.md`: the web firewall's limits, the `429` body, and `Retry-After`.
- `engineering/infrastructure/iac/README.md`: one line that page URLs are rewritten to `.html` at the edge.

### Success Criteria

#### Automated Verification

- [x] Formatting and validation pass: `cd engineering/infrastructure && just check`
- [ ] `just plan app staging` shows only the web ACL's rate rules, the new function, and the default behaviour's function association changing
- [ ] Checkov reports nothing new (the pull request's scan)

#### Manual Verification

- [ ] After `just deploy staging`: `curl -o /dev/null -w '%{http_code}' https://site.dev-pacompact.aws.focusconsulting.io/verify` and `/login` return `200`
- [ ] 301 requests to `/api/public/privilege-holders?privilege_number=PA-OK-000001` from one address inside five minutes end in `429` with the JSON body and `Retry-After: 300`
- [ ] The `/verify` page shows its "wait a few minutes" message while limited, and works again after the window

---

## Testing Strategy

### API Tests (through the endpoint, against real Postgres)

`engineering/api/tests/test_public_verification.py`:

- Signed out, search and detail both answer `200`.
- **Allow-list, by shape.** Each response model's `model_fields` equals a set written out in the test; every schema reachable from a `/api/public/` response in `openapi.json` has `additionalProperties: false`.
- **Allow-list, by content.** A practitioner with every private column set to a marker (`date_of_birth`, `npi`, `correspondence_email`, middle name, phone, residence, a `practitioner_ssn` row, `deactivation_reason` and `deactivation_note` on the privilege, an adverse action's `summary` and `action_type_code`, the license number): no marker and no `deactivation_reason` value appears in the text of either response.
- **Statuses.** Active, expired, deactivated, and encumbered privileges return `active`, `expired`, `inactive`, `inactive`. A privilege deactivated by a non-public action against the license is `inactive` with no reason (the ticket's criterion). An encumbered privilege is `inactive` whether its action is public or not, and the two responses are identical apart from the number.
- **Search.** Both names match case-insensitively and ignore surrounding spaces; a prefix does not match; a practitioner with no privilege never appears; two PAs with the same name both appear, in a stable order; a number matches in either case; paging metadata is right.
- **Validation.** Last name alone, first name alone, names with a number, no parameters, an unknown parameter, an over-long name, and a malformed number are each `422` with `VALIDATION_ERROR`.
- **Detail.** An unknown id, a malformed id, and a practitioner with no privilege: `404`, `422`, `404`, the two `404` bodies identical.
- **Dates.** `issued_on` for a privilege issued at 23:30 and at 00:30 in the reference time zone, with `issued_at` on the other UTC date; `expired` on the day after `expires_on` and `active` on the day itself, set relative to `compact_today()`: the suite has no clock to freeze, and the view reads the database's.
- The search log line carries the mode and count and neither name.

`tests/test_route_access.py` and `tests/test_openapi.py` cover the new routes without change.

### Client Tests (Vitest)

The home page (both columns; the dashboard link once signed in), the moved dashboard, the search form (both modes, required fields), results (rows, empty, `429`, failure, paging), the holder's page (cards per status, missing id, `404`), `publicApi` sends no `Authorization` header, and `expectNoAxeViolations` on each.

### E2E Tests (Playwright)

The home page test in Phase 2 and the four tests in Phase 3, each scanned for WCAG 2.1 AA.

### Manual Testing Steps

The manual criteria under each phase; the rate limit and direct loads can only be checked on staging.

## Security Impact Assessment

**Data and tier.** Public tier only: a PA's first and last name and suffix, the states of qualifying license and privilege, and each privilege's number, status, issue date, and expiry date. Rule 4 §4.5(b) names the names and states; the number, status, and dates are the Commission's Q-12 default. The practitioner's `public_id` is exposed as the detail key; it is a random UUID with no meaning.

**Flow.** Browser → CloudFront (web ACL, US-only) → load balancer → API → Postgres, read-only, TLS on every hop. No write, no email, no third party.

**Protection at each step.**

- The firewall limits one address to 300 public requests per five minutes and logs blocks to the existing alarm.
- The routes take no credentials and read no caller identity.
- The response models forbid extras and are built field by field; the tests above pin them.
- The status is collapsed before it leaves the API, so the confidential tier (non-public actions, SII, deactivation reasons) has no path into a response.

**What could go wrong.**

- *A field is added to a response model later.* The pinned field-set test fails, and the model's docstring sends the author to the allow-list document.
- *Inference from status.* Mitigated by showing every encumbered privilege as `inactive`. A watcher who records statuses over time can still see a privilege go from active to inactive; the SOW requires inactive privileges to be public, and no reason or date of the change is given.
- *Harvesting the register.* Privilege numbers are sequential per state (`PA-OK-000001`), so the number search can be walked. Everything it yields is public by rule, and the rate limit bounds the pace to 300 requests per five minutes per address. A distributed crawl is not prevented; that is accepted for public data and recorded in the feature document.
- *Search terms in logs.* Names searched travel in the query string, so CloudFront, firewall, and load-balancer access logs hold them alongside the caller's address. The API's own log line omits them. The logs are encrypted and retained under SCRUM-84's policy.
- *The firewall body drifts from `ErrorResponse`.* The client reads only the status code for `429`, so a drift costs nothing functional; the comment in `waf.tf` names `errors.py`.

## Dates and Deadlines

- **Expiry.** "Expired" is decided by `v_privilege_status` against `compact_today()`; `expires_on` is a `DATE`, inclusive (FLOW-06). No new arithmetic.
- **Issue date.** `issued_at` is an instant; the public sees the calendar day it fell on in the reference time zone, through `days.compact_date_at` (ADR-0006).
- **Boundary tests.** Listed under API Tests: issue either side of midnight in the reference time zone, and the last day of a privilege against the day after.

## Migration Notes

Not applicable: no schema change. The name search uses the existing `lower(legal_last_name)` index and filters first name on the rows it returns.

## Documentation Updates

- New: FLOW-08, in `product/`.
- Changed: `engineering/docs/data-model.md`, `roles-and-permissions.md`, `architecture.md`, `demo.md`, `design/wireframe-kit.md`, `security/infrastructure.md`; `engineering/infrastructure/iac/README.md`; `engineering/e2e/README.md`; `product/context/flows/06-state-machines.md`; `product/backlog/mvp-ticket-breakdown.md` (Q-12).
- Docstrings on every new public function, model, and route; JSDoc on every exported component and on `publicApi`.
- No dependency is added, so the inventory is unchanged.

## Performance Considerations

A name search reads the rows sharing a last name through the index, then one query for that page's privileges. A number lookup uses the unique index on `privilege_number`. Responses are not cached (`Managed-CachingDisabled` on `/api/*`), which keeps a status change visible at once. If the register grows large enough for common surnames to matter, add an index on `(lower(legal_last_name), lower(legal_first_name))`.

Public traffic shares the writer with every signed-in user, and the firewall bounds it per address, not in total. Two ways to separate it were considered and deferred to SCRUM-202, to be decided on the load-test numbers from pilot readiness (epic 12):

- **A read replica.** `instance_count = 2` already adds an Aurora reader; the public routes would take a session bound to the reader endpoint. It isolates the writer, adds failover production wants anyway, and is exact to within replication lag. It roughly doubles the database cost and adds a second engine to the API.
- **A short CloudFront cache on `/api/public/*`.** No new infrastructure, but a deactivated privilege keeps showing as active until the entry expires, and each distinct name is its own cache entry, so it helps repeated lookups and not a crawl.

The replica is the better fit for this feature, because a verification answer that is a minute stale is wrong in the direction that matters.

## References

- Original issue: SCRUM-139; contract step SCRUM-138
- Web firewall: PR #202 (`engineering/infrastructure/iac/components/app/opentofu/waf.tf`)
- Similar implementation: `engineering/api/licensing_api/routes/audit.py` (a paged read), `engineering/api/licensing_api/routes/health.py` (a `public()` router)
- CompactConnect reference: `product/context/reference/compactconnect-crosswalk.md` §6
