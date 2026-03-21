from typing import Any

from sqlalchemy.orm import scoped_session

from licensing_api.utils.logging import get_logger

logger = get_logger(__name__)


class LookupTable:
    """Representation of a database lookup table.  The purpose is to avoid hard coded enums in the src code and
    maintain flexibility in the naming of the the values

    Usage looks like this::

        class TaskType(lookup.LookupTable):
            # Model class, which must have an __init__ that matches the below code
            model = LkTaskType

            # Column names, primary key first, then description, and any other columns last
            column_names = ("task_type_id", "task_type_description")

            # Template model instances (transient, never saved to database directly)
            TRANSFER_APPLICATIONS = LkTaskType(1, "transfer")
            PROCESS_SETTLED_PAYMENTS = LkTaskType(2, "process_payments")

    Once created, it is always safe to add rows. Updating or removing rows must be done with
    caution as other tables may refer to the lookup table. Row ids can not be changed.

    Use the sync_to_database() method to add or update rows in the database to match the template
    instances. Rows will not be removed.

    Attributes of the template model instances can be used directly safely and without a database
    session::

        task_type_id = TaskType.TRANSFER_APPLICATIONS.task_type_id

    They can not be used as relationships as they are transient (not linked to a db session)::

        # Will cause an error on commit
        task.task_type = TaskType.TRANSFER_APPLICATIONS

    Instead use the get_instance() method to get an instance merged into a db session::

        task.task_type = TaskType.get_instance(db_session, template=TaskType.TRANSFER_APPLICATIONS)

    """

    model: Any = None
    column_names: tuple = ()
    # Map from template model instance (specified in the class declaration) to persistent or
    # detached model instance.
    template_instance_to_db_instance: dict[type, type]
    # Map from description (2nd column) to persistent or detached model instance.
    description_to_db_instance: dict[str, type]
    # Map from description (2nd column) to row_id.
    description_to_id: dict[str, int]

    # Caches for looking up template instances in different ways
    attr_name_to_template_instance: dict[str, type]
    id_to_template_instance: dict[int, type]
    description_to_template_instance: dict[str, type]

    @classmethod
    def repr(cls: type["LookupTable"]) -> str:
        return f"LookupTable({cls.model.__qualname__}, {cls.model.__table__.name})"

    @classmethod
    def populate_lookup_cache(cls: type["LookupTable"]) -> None:
        cls.attr_name_to_template_instance = {}
        cls.id_to_template_instance = {}
        cls.description_to_template_instance = {}

        for key, value in vars(cls).items():
            if not isinstance(value, cls.model):
                continue

            cls.insert_template_lookup_cache(key, value)

    @classmethod
    def insert_template_lookup_cache(
        cls: type["LookupTable"], key: str, template_instance: Any
    ) -> None:
        row = tuple(map(template_instance.__getattribute__, cls.column_names))
        row_id, description = row[0], row[1]

        if row_id in cls.id_to_template_instance:
            raise ValueError(f"{cls.repr()}: duplicate row id {row_id} for key {key}")

        cls.attr_name_to_template_instance[key] = template_instance
        cls.id_to_template_instance[row_id] = template_instance
        cls.description_to_template_instance[description] = template_instance

    @classmethod
    def sync_to_database(cls: type["LookupTable"], db_session: scoped_session) -> int:
        """Synchronize the lookup table to a database by adding or updating rows if needed.

        Should be called once during process initialization.

        In test cases, called once per temporary database schema."""

        if not hasattr(cls, "attr_name_to_template_instance"):
            cls.populate_lookup_cache()

        cls.template_instance_to_db_instance = {}
        cls.description_to_db_instance = {}
        cls.description_to_id = {}

        # Optimization: read all rows into db_session's identity map. This makes the get() in
        # sync_row_to_database() get the row from the identity map instead of making a query.
        _cache = db_session.query(cls.model).all()  # noqa: F841

        row_update_count = 0
        for key, template_instance in cls.attr_name_to_template_instance.items():
            if cls.sync_row_to_database(db_session, key, template_instance):
                row_update_count += 1

        if row_update_count:
            logger.info("%s: row update count %i", cls.repr(), row_update_count)

        return row_update_count

    @classmethod
    def sync_row_to_database(
        cls: type["LookupTable"], db_session: scoped_session, key: str, template_instance: Any
    ) -> bool:
        """Synchronize a single row of the lookup table to a database by adding or updating it."""
        row = tuple(map(template_instance.__getattribute__, cls.column_names))
        row_id, description = row[0], row[1]
        row_was_updated = False
        instance = db_session.query(cls.model).get(row_id)
        if instance is None:
            instance = db_session.merge(template_instance)
            logger.info("%s: add %s %r", cls.repr(), key, row)
            row_was_updated = True
        else:
            existing_values = tuple(map(instance.__getattribute__, cls.column_names))
            if row != existing_values:
                instance = db_session.merge(template_instance)
                row_was_updated = True
                logger.info("%s: update %s %r", cls.repr(), key, row)
        cls.template_instance_to_db_instance[template_instance] = instance
        cls.description_to_db_instance[description] = instance
        cls.description_to_id[description] = row_id
        return row_was_updated

    @classmethod
    def get_all(cls: type["LookupTable"]) -> list[Any]:
        """Get all instances of a model."""
        return [p for p in vars(cls).values() if isinstance(p, cls.model)]

    @classmethod
    def get_instance(
        cls: type["LookupTable"],
        db_session: scoped_session,
        template: Any | None = None,
        description: str | None = None,
    ) -> type:
        """Get an ORM instance for the row by template instance or description.

        The instance is merged into the given db session.
        """
        if template is not None and description is None:
            if not isinstance(template, cls.model):
                raise TypeError(f"template must be of type {cls.model!r}")
            if template not in cls.template_instance_to_db_instance:
                raise ValueError("template not an attribute or called before sync")
            return db_session.merge(cls.template_instance_to_db_instance[template], load=False)
        elif template is None and description is not None:
            return db_session.merge(cls.description_to_db_instance[description], load=False)
        else:
            raise TypeError("either template or description must be passed")

    @classmethod
    def get_id(cls: type["LookupTable"], description: str) -> Any:
        """Get the id for the row by description."""
        if not hasattr(cls, "description_to_template_instance"):
            cls.populate_lookup_cache()

        return getattr(cls.description_to_template_instance[description], cls.column_names[0])

    @classmethod
    def get_description(cls: type["LookupTable"], row_id: int) -> Any:
        """Get the description for the row by id."""
        if not hasattr(cls, "id_to_template_instance"):
            cls.populate_lookup_cache()

        return getattr(cls.id_to_template_instance[row_id], cls.column_names[1])
