"""Create or replace the computed-status functions and views, after every migration run.

yoyo runs this hook after the migrations, without recording it; licensing_api.migrations
runs it on every startup, so the functions always match the queries in
licensing_api/repo/status.py (ADR-0005).
"""

from yoyo import step

from licensing_api.repo.status import status_ddl

steps = [step(statement) for statement in status_ddl()]
