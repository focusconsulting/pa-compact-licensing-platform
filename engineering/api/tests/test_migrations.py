import yoyo

from licensing_api.config import settings
from licensing_api.migrations import _MIGRATIONS_DIR


def test_startup_applies_every_migration(client) -> None:
    backend = yoyo.get_backend(settings.sync_db_url)
    pending = backend.to_apply(yoyo.read_migrations(str(_MIGRATIONS_DIR)))

    assert [m.id for m in pending] == []
