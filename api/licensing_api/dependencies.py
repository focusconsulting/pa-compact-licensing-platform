from typing import Annotated

import asyncpg
from fastapi import Request
from fastapi.params import Depends


def get_db_pool(request: Request) -> asyncpg.Pool:
    """
    Dependency that provides the database connection pool from the app state.
    """
    return request.app.state.db_pool


DbPool = Annotated[asyncpg.Pool, Depends(get_db_pool)]
