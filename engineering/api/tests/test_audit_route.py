"""GET /api/commission/audit: the Commission reads the audit log."""

import uuid
from datetime import datetime, timedelta, timezone

from licensing_api.repo.audit_log import AuditLogEntry
from tests.factories import make_issued_privilege, make_user

_URL = '/api/commission/audit'


def _email() -> str:
    return f'{uuid.uuid4().hex}@example.com'


async def _entries(session) -> dict[str, str]:
    """Writes three audit rows by two staff users, an hour apart; returns the users' emails."""
    reader = await make_user(session, email=_email(), role='state_staff', state_code='KS')
    admin = await make_user(session, email=_email(), role='compact_admin')
    privilege = await make_issued_privilege(session)
    base = datetime(2026, 10, 1, tzinfo=timezone.utc)
    # Inserted directly: audit_log.write stamps the current time, and the log is append-only.
    session.add_all(
        [
            AuditLogEntry(
                occurred_at=base,
                actor_user_id=reader.id,
                action='ssn.revealed',
                entity_type='privileges',
                entity_id=privilege.id,
                reason='Case 12',
                request_id='req-a',
            ),
            AuditLogEntry(
                occurred_at=base + timedelta(hours=1),
                actor_user_id=admin.id,
                action='user.permissions_changed',
                entity_type='users',
                entity_id=reader.id,
                before={'KS': []},
                after={'KS': ['read_ssn']},
                request_id='req-b',
            ),
            AuditLogEntry(
                occurred_at=base + timedelta(hours=2),
                actor_user_id=reader.id,
                action='state.viewed',
                entity_type='states',
                entity_key='KS',
                request_id='req-c',
            ),
        ]
    )
    await session.flush()
    return {'reader': reader.email, 'admin': admin.email}


def test_the_commission_reads_entries_newest_first(client, auth_header, route_db_session):
    users = client.portal.call(_entries, route_db_session)

    response = client.get(_URL, headers=auth_header(users['admin']))

    assert response.status_code == 200
    body = response.json()
    assert body['page'] == {'number': 1, 'size': 25, 'total': 3}
    assert [e['request_id'] for e in body['data']] == ['req-c', 'req-b', 'req-a']
    permission_change = body['data'][1]
    assert permission_change['action'] == 'user.permissions_changed'
    assert permission_change['actor_email'] == users['admin']
    assert permission_change['entity_type'] == 'users'
    assert permission_change['after'] == {'KS': ['read_ssn']}
    assert body['data'][0]['entity_key'] == 'KS'
    assert body['data'][2]['reason'] == 'Case 12'


def test_filters_combine(client, auth_header, route_db_session):
    users = client.portal.call(_entries, route_db_session)
    headers = auth_header(users['admin'])

    def request_ids(**params) -> list[str]:
        response = client.get(_URL, headers=headers, params=params)
        assert response.status_code == 200
        return [e['request_id'] for e in response.json()['data']]

    assert request_ids(actor_email=users['reader']) == ['req-c', 'req-a']
    assert request_ids(actor_email=users['reader'], action='ssn.revealed') == ['req-a']
    assert request_ids(entity_type='states', entity_key='KS') == ['req-c']
    assert request_ids(
        occurred_from='2026-10-01T01:00:00Z', occurred_to='2026-10-01T02:00:00Z'
    ) == ['req-b']
    assert request_ids(sort='occurred_at', page_size=2) == ['req-a', 'req-b']
    assert request_ids(actor_email='nobody@example.com') == []


def test_an_entity_id_filter_finds_its_entries(client, auth_header, route_db_session):
    users = client.portal.call(_entries, route_db_session)
    headers = auth_header(users['admin'])
    reader_entry = client.get(_URL, headers=headers, params={'action': 'user.permissions_changed'})
    entity_id = reader_entry.json()['data'][0]['entity_id']

    response = client.get(_URL, headers=headers, params={'entity_id': entity_id})

    assert [e['request_id'] for e in response.json()['data']] == ['req-b']


def test_state_staff_may_not_read_the_audit_log(client, auth_header, route_db_session):
    users = client.portal.call(_entries, route_db_session)

    response = client.get(_URL, headers=auth_header(users['reader']))

    assert response.status_code == 403
    assert response.json()['code'] == 'FORBIDDEN'
