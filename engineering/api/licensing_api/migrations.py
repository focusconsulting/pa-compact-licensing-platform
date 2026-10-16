import logging
from pathlib import Path

import yoyo

from licensing_api.config import settings

logger = logging.getLogger(__name__)

_MIGRATIONS_DIR = Path(__file__).parent.parent / 'db-migrations'

# Migrations with this prefix only run in LOCAL_DEV (test data seeded ~1,000 years ahead so they sort last)
_LOCAL_DEV_ONLY_PREFIX = '30000101'


def run_migrations() -> None:
    logger.info('Running database migrations (environment=%s)', settings.environment)
    backend = yoyo.get_backend(settings.sync_db_url)
    all_migrations = yoyo.read_migrations(str(_MIGRATIONS_DIR))

    # locked so only one pod can attempt to run the migrations at a time
    with backend.lock():
        pending = backend.to_apply(all_migrations)
        if settings.environment != 'LOCAL_DEV':  # pragma: no cover
            pending = pending.filter(lambda m: not m.id.startswith(_LOCAL_DEV_ONLY_PREFIX))
        backend.apply_migrations_only(pending)
        # Every startup, not only when a migration applied: the status functions are
        # defined in code (ADR-0005), so a release that changes one ships no migration.
        backend.run_post_apply(all_migrations)

    logger.info('Database migrations complete')
