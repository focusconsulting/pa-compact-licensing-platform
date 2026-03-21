import json
from typing import Any, Self, TypeVar

from pydantic import TypeAdapter
from sqlalchemy import Dialect, TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import Mutable
from sqlalchemy.sql.operators import OperatorType
from sqlalchemy.sql.type_api import TypeEngine

from licensing_api.db.trackable_pydantic_type import TrackedPydanticBaseModel

_T = TypeVar("_T", bound=Any)
_P = TypeVar("_P", bound="MutablePydanticBaseModel")


class PydanticType(TypeDecorator, TypeEngine[_P]):  # type: ignore[misc]  # dual inheritance from SQLAlchemy type system has structural conflicts
    """Pydantic type.
    SAVING:
    - Uses SQLAlchemy JSON type under the hood.
    - Accepts the pydantic model and converts it to a dict on save.
    - SQLAlchemy engine JSON-encodes the dict to a string.
    RETRIEVING:
    - Pulls the string from the database.
    - SQLAlchemy engine JSON-decodes the string to a dict.
    - Uses the dict to create a pydantic model.
    """

    impl = JSONB(none_as_null=True)
    # TODO investigate if this can be true
    cache_ok = False

    def __init__(
        self: Self, pydantic_type: type[_P], sqltype: TypeEngine[_T] | None = None
    ) -> None:
        super().__init__()
        self.pydantic_type = pydantic_type
        self.sqltype = sqltype

    def coerce_compared_value(self: Self, op: OperatorType | None, value: Any) -> TypeEngine[_P]:
        return self.impl.coerce_compared_value(op, value)  # type: ignore[call-arg]  # SQLAlchemy TypeDecorator.impl type stub mismatch

    def load_dialect_impl(self: Self, dialect: Dialect) -> TypeEngine[Any]:
        return dialect.type_descriptor(JSONB(none_as_null=True))

    def process_bind_param(self: Self, value: Any, dialect: Dialect) -> dict[Any, Any] | None:
        return value.model_dump(mode="json") if value else None

    def process_result_value(self: Self, value: Any, dialect: Dialect) -> Any | None:
        return None if value is None else TypeAdapter(self.pydantic_type).validate_python(value)


class MutablePydanticBaseModel(TrackedPydanticBaseModel, Mutable):
    @classmethod
    def coerce(cls, key: str, value: Any) -> Self:
        return value if isinstance(value, cls) else cls.model_validate(value)

    def dict(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        res = super().model_dump(*args, **kwargs)
        res.pop("_parents", None)
        return res

    @classmethod
    def as_mutable(cls, sqltype: TypeEngine[_T] | None = None) -> TypeEngine[_T]:  # type: ignore[override]  # narrowing sqltype param from base class
        return super().as_mutable(PydanticType(cls, sqltype))


class CustomPydanticJSONEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:  # noqa: E741
        if isinstance(o, TrackedPydanticBaseModel):
            return o.model_dump(mode="json", exclude_none=True)
        return super().default(o)
