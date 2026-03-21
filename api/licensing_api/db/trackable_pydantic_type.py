from collections.abc import Iterable
from typing import Any, Self, SupportsIndex, TypeGuard, TypeVar
from weakref import WeakValueDictionary

from pydantic import BaseModel
from sqlalchemy.ext.mutable import Mutable

_T = TypeVar("_T", bound=Any)
_KT = TypeVar("_KT")  # Key type.
_VT = TypeVar("_VT")


parents_track: WeakValueDictionary[int, object] = WeakValueDictionary()


class TrackedObject(Mutable):
    """
    Represents an object in a nested context whose parent can be tracked.

    The top object in the parent link should be an instance of `Mutable`.
    """

    def __del__(self) -> None:
        if (id_ := id(self)) in parents_track:
            del parents_track[id_]

    def changed(self: "TrackedObject") -> None:
        if (id_ := id(self)) in parents_track:
            parent = parents_track[id_]
            if isinstance(parent, Mutable):
                parent.changed()
        elif isinstance(self, Mutable):
            super().changed()

    @classmethod
    def make_nested_trackable(cls, val: _T, parent: Mutable) -> _T:
        new_val: Any = val

        if isinstance(val, dict):
            new_val = TrackedDict((k, cls.make_nested_trackable(v, parent)) for k, v in val.items())
        elif isinstance(val, list):
            new_val = TrackedList(cls.make_nested_trackable(o, parent) for o in val)
        elif isinstance(val, BaseModel) and not isinstance(val, TrackedPydanticBaseModel):
            model_cls = type(
                "Tracked" + val.__class__.__name__, (TrackedPydanticBaseModel, val.__class__), {}
            )
            model_cls.__doc__ = (
                f"This class is composed of `{val.__class__.__name__}` and `TrackedPydanticBaseModel` "
                "to make it trackable in nested context."
            )

            # mypy struggles here since we're dynamically generated the class on 102L
            new_val = model_cls.model_validate(val.model_dump())  # type: ignore

        if isinstance(new_val, cls):
            parents_track[id(new_val)] = parent

        return new_val  # type: ignore[return-value]  # dynamic type wrapping preserves _T at runtime


class TrackedDict(TrackedObject, dict[_KT, _VT]):
    """
    A trackable object that inherits from dict
    """

    def __setitem__(self, key: _KT, value: _VT) -> None:
        """Detect dictionary set events and emit change events."""
        super().__setitem__(key, value)
        self.changed()

    def setdefault(self, key: _KT, value: _VT = None) -> _VT:  # type: ignore[assignment,override]  # aligning with MutableMapping while keeping tracking
        result = super().setdefault(key, TrackedObject.make_nested_trackable(value, self))
        self.changed()
        return result

    def __delitem__(self, key: _KT) -> None:
        """Detect dictionary del events and emit change events."""
        super().__delitem__(key)
        self.changed()

    def update(self: Self, *a: Any, **kw: _VT) -> None:
        a = tuple(TrackedObject.make_nested_trackable(e, self) for e in a)
        kw = {k: TrackedObject.make_nested_trackable(v, self) for k, v in kw.items()}
        super().update(*a, **kw)
        self.changed()

    def pop(self, *arg: Any) -> _VT:
        result = super().pop(*arg)
        self.changed()
        return result

    def popitem(self) -> tuple[_KT, _VT]:
        result = super().popitem()
        self.changed()
        return result

    def clear(self) -> None:
        super().clear()
        self.changed()

    def __setstate__(self, state: dict[str, int] | dict[str, str]) -> None:
        self.update(state)


class TrackedList(TrackedObject, list[_T]):
    """
    A trackable object that inherits from list
    """

    def __reduce_ex__(self, proto: SupportsIndex) -> tuple[type, tuple[list[int]]]:
        return (self.__class__, (list(self),))

    def __setstate__(self, state: Iterable[_T]) -> None:
        self[:] = state

    def is_scalar(self, value: _T | Iterable[_T]) -> TypeGuard[_T]:
        return not isinstance(value, Iterable)

    def is_iterable(self, value: _T | Iterable[_T]) -> TypeGuard[Iterable[_T]]:
        return isinstance(value, Iterable)

    # __setitem__ is overloaded and these are the collapsed types, but this requires ignore the type checking on 137L
    def __setitem__(self, index: SupportsIndex | slice, value: _T | Iterable[_T]) -> None:
        """Detect list set events and emit change events."""
        super().__setitem__(index, TrackedObject.make_nested_trackable(value, self))  # type: ignore
        self.changed()

    def __delitem__(self, index: SupportsIndex | slice) -> None:
        """Detect list del events and emit change events."""
        super().__delitem__(index)
        self.changed()

    def pop(self, *arg: SupportsIndex) -> _T:
        result = super().pop(*arg)
        self.changed()
        return result

    def append(self, x: _T) -> None:
        super().append(TrackedObject.make_nested_trackable(x, self))
        self.changed()

    def extend(self, x: Iterable[_T]) -> None:
        super().extend(x)
        self.changed()

    # https://github.com/python/mypy/issues/6225
    def __iadd__(self, x: Iterable[_T]) -> Self:  # type: ignore
        self.extend(TrackedObject.make_nested_trackable(v, self) for v in x)
        return self

    def insert(self, i: SupportsIndex, x: _T) -> None:
        super().insert(i, TrackedObject.make_nested_trackable(x, self))
        self.changed()

    def remove(self, i: _T) -> None:
        super().remove(i)
        self.changed()

    def clear(self) -> None:
        super().clear()
        self.changed()

    def sort(self, **kw: Any) -> None:
        super().sort(**kw)
        self.changed()

    def reverse(self) -> None:
        super().reverse()
        self.changed()


class MutableList(TrackedList, Mutable, list[_T]):
    """
    A mutable list that tracks changes to itself and its children.

    Used as top-level mapped object. e.g.

        aliases: Mapped[list[str]] = mapped_column(MutableList.as_mutable(ARRAY(String(128))))
        schedule: Mapped[list[list[str]]] = mapped_column(MutableList.as_mutable(ARRAY(sa.String(128), dimensions=2)))
    """

    @classmethod
    def coerce(cls, key: str, value: list[_T]) -> Self:
        return value if isinstance(value, cls) else cls(value)

    def __init__(self, __iterable: Iterable[_T]):
        super().__init__(TrackedObject.make_nested_trackable(__iterable, self))


class MutableDict(TrackedDict, Mutable):
    """
    A mutable list that tracks changes to itself and its children.

    Used as top-level mapped object. e.g.

        fields: Mapped[dict[str, str]] = mapped_column(MutableDict.as_mutable()))
    """

    @classmethod
    def coerce(cls, key: str, value: Any) -> TrackedDict:
        return value if isinstance(value, cls) else cls(value)

    def __init__(self, source: Any = (), **kwds: Any) -> None:
        super().__init__(TrackedObject.make_nested_trackable(dict(source, **kwds), self))


class TrackedPydanticBaseModel(TrackedObject, BaseModel):
    """
    A tracked object that inherits from any pydantic model
    """

    @classmethod
    def coerce(cls, key: str, value: Any) -> Self:
        return value if isinstance(value, cls) else cls.model_validate(value)

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        for field_name in self.model_fields.keys():
            setattr(
                self,
                field_name,
                TrackedObject.make_nested_trackable(getattr(self, field_name), self),
            )

    def __setattr__(self, name: str, value: Any) -> None:
        prev_value = getattr(self, name, None)
        super().__setattr__(name, value)
        if prev_value != getattr(self, name):
            self.changed()
