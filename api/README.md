# API

## Table of contents

-   [Developer Setup](./README.md#developer-setup)
-   [Key Tooling](./README.md#key-tooling)
-   [Type Checking](./README.md#type-checking)
-   [DB Migrations](./README.md#db-migrations)

## Developer Setup

Please make sure that you have completed all the steps in the [root setup](../README.md#developer-setup)

1. Run `poetry config virtualenvs.in-project true` so that virtual environment is created in this directory
2. Run `poetry install --no-root`
3. Verify that everything has worked by running `make lint`

### Running commands

The API code uses a makefile in order to capture the commands that need to get run as part of working on this part of the project. Details on the commands can be seen by running `make help`.

## Key Tooling

-   [connexion](https://connexion.readthedocs.io/en/stable/): spec-first API framework that in addition to providing a web framework for creating APIs, consumes the [openapi.yaml](./openapi.yaml) and provides mocking and validation
-   [sqlalchemy](https://docs.sqlalchemy.org/en/20/index.html): Handles talking to the DB as well as provides an ORM layer for the application
-   [pydantic](https://docs.pydantic.dev/latest/): general purpose data validation library
-   [alembic](https://alembic.sqlalchemy.org/en/latest/): tool for authoring and applying database migrations. See [migrations](./README.md#migrations) for more details

More details and considerations around this tooling can be found in [docs](../docs/architecture_decision_records/README.md)

## Type checking

The python code is statically checked using a tool called [MyPy](https://mypy.readthedocs.io/en/stable/index.html) which implements the spec defined in [PEP-0484](https://peps.python.org/pep-0484/) and is used as part of the linting process. The goal is enforce types everywhere as this provides more guarantees that code will operate as expected in production and reduces the risk of a runtime error occurring. The team aims to reduce the use of `# type: ignore` as much as possible and the CI steps guarantee that all merged code passes the type checker

## DB Migrations

TODO
