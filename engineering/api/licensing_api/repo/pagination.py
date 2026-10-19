from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy import ColumnElement, Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from licensing_api.responses import PageQuery


async def paginate[M](
    session: AsyncSession,
    statement: Select[tuple[M]],
    query: PageQuery,
    columns: Mapping[str, ColumnElement[Any]],
    tiebreaker: ColumnElement[Any],
) -> tuple[list[M], int]:
    """One page of ``statement``'s rows and the total row count.

    ``columns`` maps each sortable field name to its column. ``tiebreaker`` is a unique
    column sorted last, so rows with equal sort values keep one order across pages.
    """
    total = await session.scalar(
        select(func.count()).select_from(statement.order_by(None).subquery())
    )
    order = [
        columns[key.field].desc() if key.descending else columns[key.field].asc()
        for key in query.sort
    ]
    page = statement.order_by(*order, tiebreaker).limit(query.page_size).offset(query.offset)
    return list((await session.scalars(page)).all()), total or 0
