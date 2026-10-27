import base64
import uuid
from collections.abc import AsyncGenerator, Callable, Generator
from unittest.mock import patch

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from jose import jwt as jose_jwt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncSession,
    AsyncTransaction,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from licensing_api.__main__ import app
from licensing_api.config import Settings, get_settings
from licensing_api.dependencies import get_db_session
from tests.record_guard import RecordGuard

TEST_SETTINGS = Settings(
    cognito_client_id='test-client-id', cognito_user_pool_id='us-east-1_testpool'
)

_TEST_CLIENT_ID = 'test-client-id'
_TEST_KID = 'test-key-1'


def _int_to_base64url(n: int) -> str:
    length = (n.bit_length() + 7) // 8
    return base64.urlsafe_b64encode(n.to_bytes(length, 'big')).rstrip(b'=').decode()


@pytest.fixture(scope='module')
def _private_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(scope='module')
def jwks(_private_key):
    pub = _private_key.public_key().public_numbers()
    return {
        'keys': [
            {
                'kty': 'RSA',
                'use': 'sig',
                'alg': 'RS256',
                'kid': _TEST_KID,
                'n': _int_to_base64url(pub.n),
                'e': _int_to_base64url(pub.e),
            }
        ]
    }


@pytest.fixture(scope='module')
def client(jwks):
    # dependency_overrides replaces the stored function reference FastAPI holds
    # inside Depends(get_settings), which patch() on the module name cannot reach.
    app.dependency_overrides[get_settings] = lambda: TEST_SETTINGS
    with patch('licensing_api.auth._get_jwks', return_value=jwks):
        with TestClient(app) as c:
            yield c
    app.dependency_overrides.clear()


@pytest.fixture
async def db_session(client) -> AsyncGenerator[AsyncSession]:
    """A session whose work is rolled back when the test ends, so tests never see each other's rows.

    Depends on ``client`` so the app's lifespan has applied the migrations. Code
    under test may commit: with ``create_savepoint`` a commit releases a
    savepoint inside the outer transaction, which is still rolled back.
    """
    engine = create_async_engine(TEST_SETTINGS.db_url, poolclass=NullPool)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(
            bind=connection, join_transaction_mode='create_savepoint', expire_on_commit=False
        )
        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()
    await engine.dispose()


# Tables the Worker's and jobs' code writes in their own transactions, in the order their rows are deleted.
_WORKER_TABLES = ('job_runs', 'notifications', 'domain_event_deliveries', 'domain_events')


@pytest.fixture
async def committed_sessions(client) -> AsyncGenerator[async_sessionmaker[AsyncSession]]:
    """Sessions that really commit, for code that opens its own transactions, such as the dispatcher.

    Every Worker-table row the test leaves is deleted afterwards. Rows the test
    commits elsewhere are its own to remove.
    """
    # Pooled, as the Worker's engine is, so timings are realistic.
    engine = create_async_engine(TEST_SETTINGS.db_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        # Raw SQL: these tables are listed by name, and the ORM has nothing to add to a bulk delete.
        leftovers = {
            table: (await session.execute(text(f'SELECT count(*) FROM {table}'))).scalar_one()
            for table in _WORKER_TABLES
        }
    assert not any(leftovers.values()), f'Rows left by an earlier test: {leftovers}'
    try:
        yield factory
    finally:
        async with factory() as session, session.begin():
            for table in _WORKER_TABLES:
                await session.execute(text(f'DELETE FROM {table}'))
        await engine.dispose()


@pytest.fixture
def route_db_session(client) -> Generator[AsyncSession]:
    """Gives every route in the test one session whose work is rolled back when the test ends.

    Use it for any test that calls a route which writes. The session lives on the
    app's event loop, so read it in the test through ``client.portal.call``. A
    route's commit releases a savepoint inside the outer transaction, which is
    still rolled back. The test fails if a route commits a change without an event.
    """

    async def _open() -> tuple[AsyncConnection, AsyncTransaction, AsyncSession]:
        connection = await app.state.db_engine.connect()
        transaction = await connection.begin()
        session = AsyncSession(
            bind=connection, join_transaction_mode='create_savepoint', expire_on_commit=False
        )
        return connection, transaction, session

    connection, transaction, session = client.portal.call(_open)
    guard = RecordGuard(session)

    async def _session_override() -> AsyncGenerator[AsyncSession]:
        yield session

    app.dependency_overrides[get_db_session] = _session_override
    try:
        yield session
    finally:
        app.dependency_overrides.pop(get_db_session, None)

        async def _close() -> None:
            await session.close()
            await transaction.rollback()
            await connection.close()

        client.portal.call(_close)
    assert not guard.violations, guard.violations


@pytest.fixture(scope='module')
def auth_header(_private_key) -> Callable[[str], dict]:
    """Returns a helper that builds a signed Authorization Bearer header for the given email."""

    def _make(email: str) -> dict:
        token = jose_jwt.encode(
            {
                'sub': str(uuid.uuid5(uuid.NAMESPACE_URL, email)),
                'email': email,
                'token_use': 'id',
                'aud': _TEST_CLIENT_ID,
            },
            _private_key,
            algorithm='RS256',
            headers={'kid': _TEST_KID},
        )
        return {'Authorization': f'Bearer {token}'}

    return _make
