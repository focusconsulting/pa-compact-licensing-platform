"""The attestations catalogue: its seed, its current versions, and what an application accepted (SCRUM-110)."""

import re

import pytest
from sqlalchemy import text
from sqlmodel import col, select

from licensing_api.context import ChangeContext
from licensing_api.repo.attestation import (
    Attestation,
    AttestationAppliesTo,
    ParticipationApplicationAttestation,
    accept,
    current_attestations,
    out_of_date_codes,
)
from tests.factories import assert_rejected, make_application, make_practitioner, system_user_id

_PARTICIPATION = [
    'arc_pa_graduate',
    'nccpa_current',
    'no_convictions',
    'no_controlled_substance_action',
    'no_current_restriction',
    'two_year_bar',
    'no_pending_investigation',
    'service_of_process',
    'background_check',
    'truthfulness',
]


async def _context(session) -> ChangeContext:
    return ChangeContext(await system_user_id(session), 'req-attest')


async def _current(session, applies_to=AttestationAppliesTo.PARTICIPATION) -> list[Attestation]:
    return list((await session.scalars(current_attestations(applies_to))).all())


async def _add_version(session, code: str, version: int, /, **overrides) -> Attestation:
    original = await session.get(Attestation, (code, 1))
    fields = {
        'code': code,
        'version': version,
        'applies_to': original.applies_to,
        'sort_order': original.sort_order,
        'text': f'{original.text} (reworded)',
        'source': original.source,
        'created_by': await system_user_id(session),
    }
    fields.update(overrides)
    attestation = Attestation(**fields)
    session.add(attestation)
    await session.flush()
    return attestation


async def _application_id(session) -> int:
    application = await make_application(session, await make_practitioner(session))
    assert application.id is not None
    return application.id


async def test_the_seed_asks_for_each_participation_attestation_in_order(db_session):
    assert [a.code for a in await _current(db_session)] == _PARTICIPATION


async def test_the_seed_asks_for_supervision_and_prescribing_compliance_on_a_privilege(db_session):
    codes = [a.code for a in await _current(db_session, AttestationAppliesTo.PRIVILEGE)]

    assert codes == ['supervision_compliance', 'prescribing_compliance']


async def test_every_seeded_attestation_cites_a_rule_or_model_legislation_clause(db_session):
    seeded = (await db_session.scalars(select(Attestation))).all()

    uncited = [
        a.code for a in seeded if not re.fullmatch(r'(Rule 3|ML) §\S+(; ML §\S+)?', a.source)
    ]
    assert uncited == []


async def test_a_new_version_becomes_current(db_session):
    await _add_version(db_session, 'nccpa_current', 2)

    current = {a.code: a.version for a in await _current(db_session)}

    assert current['nccpa_current'] == 2


async def test_a_retired_attestation_is_no_longer_asked_for(db_session):
    attestation = await db_session.get(Attestation, ('two_year_bar', 1))
    attestation.retired_at = attestation.created_at
    await db_session.flush()

    assert 'two_year_bar' not in [a.code for a in await _current(db_session)]


async def test_a_state_s_own_attestation_is_not_asked_of_every_state(db_session):
    await _add_version(
        db_session,
        'supervision_compliance',
        1,
        code='ks_jurisprudence',
        state_code='KS',
        source='Rule 3 §3.3(a)(9)',
    )

    codes = [a.code for a in await _current(db_session, AttestationAppliesTo.PRIVILEGE)]

    assert 'ks_jurisprudence' not in codes


async def test_only_a_privilege_attestation_belongs_to_one_state(db_session):
    await assert_rejected(
        db_session,
        "UPDATE attestations SET state_code = 'KS' WHERE code = 'nccpa_current'",
    )
    await assert_rejected(
        db_session,
        'INSERT INTO attestations (code, version, applies_to, state_code, sort_order, text, source, created_by) '
        "SELECT 'x', 1, 'participation', 'KS', 1, 'x', 'Rule 3 §3.4', id FROM users LIMIT 1",
    )


@pytest.mark.parametrize('column', ['text', 'source', 'applies_to'])
async def test_an_attestation_s_wording_cannot_be_rewritten(db_session, column):
    value = 'privilege' if column == 'applies_to' else 'changed'

    await assert_rejected(
        db_session,
        f"UPDATE attestations SET {column} = :value WHERE code = 'nccpa_current'",
        {'value': value},
    )


async def test_an_attestation_without_a_source_is_refused(db_session):
    await assert_rejected(
        db_session,
        'INSERT INTO attestations (code, version, applies_to, sort_order, text, source, created_by) '
        "SELECT 'x', 1, 'participation', 1, 'x', '', id FROM users LIMIT 1",
    )


async def test_an_application_with_nothing_accepted_is_out_of_date_on_every_code(db_session):
    application_id = await _application_id(db_session)

    assert await out_of_date_codes(db_session, application_id) == _PARTICIPATION


async def test_accepting_every_current_version_leaves_nothing_out_of_date(db_session):
    application_id = await _application_id(db_session)
    ctx = await _context(db_session)

    for attestation in await _current(db_session):
        await accept(db_session, ctx, application_id, attestation)

    assert await out_of_date_codes(db_session, application_id) == []


async def test_a_stale_version_is_out_of_date(db_session):
    application_id = await _application_id(db_session)
    ctx = await _context(db_session)
    for attestation in await _current(db_session):
        await accept(db_session, ctx, application_id, attestation)

    await _add_version(db_session, 'no_pending_investigation', 2)

    assert await out_of_date_codes(db_session, application_id) == ['no_pending_investigation']


async def test_accepting_a_newer_version_keeps_the_older_acceptance(db_session):
    application_id = await _application_id(db_session)
    ctx = await _context(db_session)
    await accept(
        db_session, ctx, application_id, await db_session.get(Attestation, ('nccpa_current', 1))
    )
    await accept(
        db_session, ctx, application_id, await _add_version(db_session, 'nccpa_current', 2)
    )

    versions = (
        await db_session.scalars(
            select(ParticipationApplicationAttestation.attestation_version).where(
                col(ParticipationApplicationAttestation.participation_application_id)
                == application_id
            )
        )
    ).all()

    assert sorted(versions) == [1, 2]


async def test_accepting_the_same_version_twice_records_it_once(db_session):
    application_id = await _application_id(db_session)
    ctx = await _context(db_session)
    attestation = await db_session.get(Attestation, ('nccpa_current', 1))

    await accept(db_session, ctx, application_id, attestation)
    await accept(db_session, ctx, application_id, attestation)

    count = await db_session.scalar(
        text(
            'SELECT count(*) FROM participation_application_attestations '
            'WHERE participation_application_id = :id'
        ),
        {'id': application_id},
    )
    assert count == 1


async def test_a_privilege_attestation_cannot_be_accepted_on_a_participation_application(
    db_session,
):
    application_id = await _application_id(db_session)
    attestation = await db_session.get(Attestation, ('supervision_compliance', 1))

    with pytest.raises(ValueError, match='not a participation attestation'):
        await accept(db_session, await _context(db_session), application_id, attestation)


@pytest.mark.parametrize(
    'statement',
    [
        'UPDATE participation_application_attestations SET accepted_at = now()',
        'DELETE FROM participation_application_attestations',
    ],
)
async def test_an_acceptance_is_never_changed_or_removed(db_session, statement):
    application_id = await _application_id(db_session)
    await accept(
        db_session,
        await _context(db_session),
        application_id,
        await db_session.get(Attestation, ('nccpa_current', 1)),
    )

    await assert_rejected(db_session, statement)
