import logging
from pathlib import Path

import yoyo

from licensing_api.config import settings

logger = logging.getLogger(__name__)

_MIGRATIONS_DIR = Path(__file__).parent.parent / 'db-migrations'


def run_migrations() -> None:
    logger.info('Running database migrations (environment=%s)', settings.environment)
    backend = yoyo.get_backend(settings.sync_db_url)
    all_migrations = yoyo.read_migrations(str(_MIGRATIONS_DIR))

    # locked so only one pod can attempt to run the migrations at a time
    with backend.lock():
        backend.apply_migrations_only(backend.to_apply(all_migrations))
        # Every startup, not only when a migration applied: the status functions are
        # defined in code (ADR-0005), so a release that changes one ships no migration.
        backend.run_post_apply(all_migrations)

    logger.info('Database migrations complete')
