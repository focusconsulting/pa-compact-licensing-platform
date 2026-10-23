"""Response shapes, page_query(), and paginate() (backlog D3). Every /api route answers with Data, Paged, or no body."""

from typing import Annotated

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from pydantic import BaseModel
from sqlmodel import col, select

from licensing_api.__main__ import app
from licensing_api.errors import AppError, ErrorCode, app_error_handler, validation_error_handler
from licensing_api.repo.pagination import paginate
from licensing_api.repo.state import State
from licensing_api.responses import Data, Page, Paged, PageQuery, SortKey, page_query

_items = FastAPI()
_items.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
_items.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]


@_items.get('/items', name='Items', description='Echoes the page query')
async def items(
    query: Annotated[PageQuery, page_query('name', 'created', default_sort='-created')],
) -> dict:
    return {
        'page': query.page,
        'page_size': query.page_size,
        'offset': query.offset,
        'sort': [[key.field, key.descending] for key in query.sort],
    }


@pytest.fixture(scope='module')
def items_client():
    with TestClient(_items) as client:
        yield client


def test_data_and_paged_wrap_their_content():
    assert Data[int](data=3).model_dump() == {'data': 3}
    page = PageQuery(page=2, page_size=10, sort=()).page_of(total=31)
    assert Paged[str](data=['a'], page=page).model_dump() == {
        'data': ['a'],
        'page': {'number': 2, 'size': 10, 'total': 31},
    }


def test_page_query_defaults(items_client):
    assert items_client.get('/items').json() == {
        'page': 1,
        'page_size': 25,
        'offset': 0,
        'sort': [['created', True]],
    }


def test_page_query_reads_page_size_and_sort(items_client):
    response = items_client.get(
        '/items', params={'page': 3, 'page_size': 10, 'sort': 'name, -created,'}
    )

    assert response.json() == {
        'page': 3,
        'page_size': 10,
        'offset': 20,
        'sort': [['name', False], ['created', True]],
    }


@pytest.mark.parametrize('params', [{'page': 0}, {'page_size': 0}, {'page_size': 101}])
def test_page_query_rejects_out_of_range_values(items_client, params):
    response = items_client.get('/items', params=params)

    assert response.status_code == 422
    assert response.json()['code'] == ErrorCode.ValidationError


def test_page_query_rejects_an_unsortable_field(items_client):
    response = items_client.get('/items', params={'sort': 'name,-ssn'})

    assert response.status_code == 422
    assert response.json() == {
        'code': ErrorCode.ValidationError,
        'details': ['query.sort: cannot sort by ssn'],
    }


def test_page_query_rejects_an_unsortable_default():
    with pytest.raises(ValueError, match='not sortable'):
        page_query('name', default_sort='created')


_FIVE_STATES = ('KS', 'NE', 'OK', 'IA', 'MO')


async def _page(db_session, number: int, *sort: SortKey) -> tuple[list[str], int]:
    statement = select(State).where(col(State.code).in_(_FIVE_STATES))
    rows, total = await paginate(
        db_session,
        statement,
        PageQuery(page=number, page_size=2, sort=sort),
        {'name': col(State.name)},
        tiebreaker=col(State.code),
    )
    return [state.code for state in rows], total


async def test_paginate_returns_a_page_and_the_total(db_session):
    by_name = SortKey(field='name', descending=False)

    assert await _page(db_session, 1, by_name) == (['IA', 'KS'], 5)
    assert await _page(db_session, 2, by_name) == (['MO', 'NE'], 5)
    assert await _page(db_session, 3, by_name) == (['OK'], 5)
    assert await _page(db_session, 4, by_name) == ([], 5)


async def test_paginate_sorts_descending_and_breaks_ties(db_session):
    assert await _page(db_session, 1, SortKey(field='name', descending=True)) == (['OK', 'NE'], 5)
    assert await _page(db_session, 1) == (['IA', 'KS'], 5)


def test_a_page_reports_its_position():
    assert PageQuery(page=1, page_size=25, sort=()).page_of(0) == Page(number=1, size=25, total=0)


# Routes still answering with a bare body. /api/me moves to Data with the generated client (SCRUM-79).
_UNWRAPPED = {'/api/me'}


def _bare_bodies(routes: list) -> list[str]:
    """The /api routes outside /api/health whose body is neither Data, Paged, nor empty."""
    return [
        route.path
        for route in routes
        if isinstance(route, APIRoute)
        and route.path.startswith('/api')
        and not route.path.startswith('/api/health')
        and route.path not in _UNWRAPPED
        and not (route.response_model is None or issubclass(route.response_model, (Data, Paged)))
    ]


def test_every_api_route_answers_with_data_paged_or_no_body():
    assert _bare_bodies(app.routes) == []


class _Thing(BaseModel):
    name: str


_shapes = FastAPI()


@_shapes.get('/api/data', name='Data', description='One thing')
async def one() -> Data[_Thing]:
    return Data(data=_Thing(name='a'))


@_shapes.get('/api/paged', name='Paged', description='A page of things')
async def many() -> Paged[_Thing]:
    return Paged(data=[], page=Page(number=1, size=25, total=0))


@_shapes.delete('/api/empty', name='Empty', description='No body', status_code=204)
async def empty() -> None:
    return None


@_shapes.get('/api/bare', name='Bare', description='A bare thing')
async def bare() -> _Thing:
    return _Thing(name='a')


def test_only_a_bare_body_breaks_the_envelope():
    assert _bare_bodies(_shapes.routes) == ['/api/bare']
