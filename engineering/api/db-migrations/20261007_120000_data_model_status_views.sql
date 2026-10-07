-- Migration: computed status (F-02 phase 3)
-- Created: 2026-10-07
-- Status a rule derives is computed on read, never stored (D1, ADR-0005). These
-- three functions are the only place status day arithmetic lives (ADR-0006):
-- each takes the date to evaluate, so tests and reports can ask "as of" any day.
-- End dates are inclusive.

-- ---------------------------------------------------------------------------
-- Qualifying license status
-- ---------------------------------------------------------------------------
-- Precedence: voluntarily terminated, then any non-active status the state
-- reports, then past expiry, then an adverse action in force, else active.
-- The reported status is the current one; as_of applies to the dates.

CREATE FUNCTION qualifying_license_status_on(as_of DATE)
    RETURNS TABLE (qualifying_license_id BIGINT, status TEXT)
    LANGUAGE sql STABLE AS
$$
SELECT ql.id,
       CASE
           WHEN ql.terminated_on IS NOT NULL AND ql.terminated_on <= as_of THEN 'terminated'
           WHEN ql.state_reported_status <> 'active' THEN ql.state_reported_status
           WHEN ql.expires_on IS NOT NULL AND as_of > ql.expires_on THEN 'expired'
           WHEN EXISTS (SELECT 1
                        FROM adverse_actions aa
                        WHERE aa.qualifying_license_id = ql.id
                          AND aa.effective_from <= as_of
                          AND (aa.effective_until IS NULL OR aa.effective_until >= as_of))
               THEN 'encumbered'
           ELSE 'active'
       END
FROM qualifying_licenses ql
$$;

-- ---------------------------------------------------------------------------
-- Privilege status (FLOW-06)
-- ---------------------------------------------------------------------------
-- Precedence (ADR-0005): inactive, with the deactivation reason; then past the
-- pinned expiry; then an adverse action against the privilege in force; else
-- active. An action against the qualifying license reaches privileges through
-- the cascade that deactivates them (FLOW-05), not through this function.

CREATE FUNCTION privilege_status_on(as_of DATE)
    RETURNS TABLE (privilege_id BIGINT, status TEXT, status_reason TEXT)
    LANGUAGE sql STABLE AS
$$
SELECT p.id,
       CASE
           WHEN p.administrator_status = 'inactive' THEN 'inactive'
           WHEN as_of > p.expires_on THEN 'expired'
           WHEN EXISTS (SELECT 1
                        FROM adverse_actions aa
                        WHERE aa.privilege_id = p.id
                          AND aa.effective_from <= as_of
                          AND (aa.effective_until IS NULL OR aa.effective_until >= as_of))
               THEN 'encumbered'
           ELSE 'active'
       END,
       CASE WHEN p.administrator_status = 'inactive' THEN p.deactivation_reason END
FROM privileges p
$$;

-- ---------------------------------------------------------------------------
-- Compact eligibility: the two-year bar (ML §4.A.8)
-- ---------------------------------------------------------------------------
-- A PA is barred while an adverse action against a qualifying license is in
-- force, and for two years from "the date on which the License ... is no longer
-- limited or restricted". effective_until is the last restricted day (inclusive),
-- so that date is effective_until + 1 day. eligible_again_on is NULL while any
-- such action has no end date. Actions that start after as_of are ignored.

CREATE FUNCTION compact_eligibility_on(as_of DATE)
    RETURNS TABLE (practitioner_id BIGINT, is_barred BOOLEAN, eligible_again_on DATE)
    LANGUAGE sql STABLE AS
$$
WITH started AS (
    SELECT aa.practitioner_id,
           (aa.effective_until + 1 + INTERVAL '2 years')::date AS bar_ends_on,
           aa.effective_until IS NULL                          AS is_open_ended
    FROM adverse_actions aa
    WHERE aa.against = 'qualifying_license'
      AND aa.effective_from <= as_of
),
per_practitioner AS (
    SELECT s.practitioner_id,
           bool_or(s.is_open_ended) AS has_open_ended,
           max(s.bar_ends_on)       AS latest_bar_end
    FROM started s
    GROUP BY s.practitioner_id
)
SELECT pr.id,
       COALESCE(pp.has_open_ended OR as_of < pp.latest_bar_end, FALSE),
       CASE WHEN pp.has_open_ended THEN NULL ELSE pp.latest_bar_end END
FROM practitioners pr
LEFT JOIN per_practitioner pp ON pp.practitioner_id = pr.id
$$;

-- ---------------------------------------------------------------------------
-- Views: each function as of today in the reference time zone (ADR-0006)
-- ---------------------------------------------------------------------------

CREATE VIEW v_qualifying_license_status AS
SELECT qualifying_license_id, status FROM qualifying_license_status_on(compact_today());

CREATE VIEW v_privilege_status AS
SELECT privilege_id, status, status_reason FROM privilege_status_on(compact_today());

CREATE VIEW v_compact_eligibility AS
SELECT practitioner_id, is_barred, eligible_again_on FROM compact_eligibility_on(compact_today());
