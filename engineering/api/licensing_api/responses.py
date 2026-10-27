"""The success shapes every route returns, and the paging and sorting query parameters (backlog D3)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Depends, Query
from pydantic import BaseModel, ConfigDict

from licensing_api.errors import AppError, ErrorCode

MAX_PAGE_SIZE = 100


def example(**fields: Any) -> Callable[[dict[str, Any], type[BaseModel]], None]:
    """A ``json_schema_extra`` whose example is the model built from ``fields``, so one that drifts from the model fails."""

    def add(schema: dict[str, Any], model: type[BaseModel]) -> None:
        schema['examples'] = [model(**fields).model_dump(mode='json')]

    return add


class Data[T](BaseModel):
    """``{"data": ...}``: one resource. Errors use ``ErrorResponse``, never this."""

    data: T


class Page(BaseModel):
    """Where a page sits in a list: its 1-based ``number``, its ``size``, and the ``total`` count across all pages."""

    model_config = ConfigDict(json_schema_extra=example(number=1, size=25, total=1))

    number: int
    size: int
    total: int


class Paged[T](BaseModel):
    """``{"data": [...], "page": {...}}``: one page of a list."""

    data: list[T]
    page: Page


@dataclass(frozen=True)
class SortKey:
    """One field in a ``sort`` parameter, and whether it sorts descending."""

    field: str
    descending: bool


@dataclass(frozen=True)
class PageQuery:
    """A validated ``?page=&page_size=&sort=`` request."""

    page: int
    page_size: int
    sort: tuple[SortKey, ...]

    @property
    def offset(self) -> int:
        """The number of rows to skip to reach this page."""
        return (self.page - 1) * self.page_size

    def page_of(self, total: int) -> Page:
        """The ``Page`` metadata for this request, given the ``total`` count."""
        return Page(number=self.page, size=self.page_size, total=total)


def page_query(*sortable: str, default_sort: str) -> Any:
    """``Depends`` reading ``?page=1&page_size=25&sort=field,-field``; ``-`` sorts descending.

    Only fields in ``sortable`` may be sorted on; anything else is a 422.
    """
    defaults = _parse_sort(default_sort)
    if unknown := [key.field for key in defaults if key.field not in sortable]:
        raise ValueError(f'default_sort names fields that are not sortable: {unknown}')

    async def read(
        page: Annotated[int, Query(ge=1)] = 1,
        page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = 25,
        sort: Annotated[str | None, Query()] = None,
    ) -> PageQuery:
        keys = _parse_sort(sort) if sort else defaults
        if unknown := [key.field for key in keys if key.field not in sortable]:
            raise AppError(
                422,
                ErrorCode.ValidationError,
                [f'query.sort: cannot sort by {field}' for field in unknown],
            )
        return PageQuery(page=page, page_size=page_size, sort=keys)

    return Depends(read)


def _parse_sort(value: str) -> tuple[SortKey, ...]:
    return tuple(
        SortKey(field=part.removeprefix('-'), descending=part.startswith('-'))
        for part in (piece.strip() for piece in value.split(','))
        if part
    )
