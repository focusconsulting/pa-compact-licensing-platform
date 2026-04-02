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
    backend = yoyo.get_backend(settings.db_url)
    all_migrations = yoyo.read_migrations(str(_MIGRATIONS_DIR))

    # locked so only one pod can attempt to run the migrations at a time
    with backend.lock():
        pending = backend.to_apply(all_migrations)
        if settings.environment != 'LOCAL_DEV':
            pending = [m for m in pending if not m.id.startswith(_LOCAL_DEV_ONLY_PREFIX)]
        backend.apply_migrations(pending)

    logger.info('Database migrations complete')
