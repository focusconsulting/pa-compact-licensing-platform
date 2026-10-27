-- Migration: job runs (SCRUM-80)
-- Created: 2026-10-27
-- Backlog: D8 (scheduled jobs run as ECS tasks)

-- One row per run of a scheduled job. A run whose task died before it finished
-- keeps a NULL outcome.
CREATE TABLE job_runs (
    id           BIGSERIAL   PRIMARY KEY,
    job          TEXT        NOT NULL,
    started_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at  TIMESTAMPTZ,
    outcome      TEXT,
    error        TEXT,
    CONSTRAINT chk_job_runs_outcome CHECK (outcome IN ('succeeded', 'failed')),
    CONSTRAINT chk_job_runs_finished_at CHECK ((outcome IS NULL) = (finished_at IS NULL))
);

CREATE INDEX idx_job_runs_job_started_at ON job_runs (job, started_at DESC);
