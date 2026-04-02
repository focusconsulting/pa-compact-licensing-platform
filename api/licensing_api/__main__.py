import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import asyncpg
import uvicorn
from fastapi import FastAPI

from licensing_api.config import settings
from licensing_api.migrations import run_migrations
from licensing_api.routes.health import router

logging.basicConfig(level=settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    await asyncio.to_thread(run_migrations)
    app.state.db_pool = await asyncpg.create_pool(settings.db_url)
    yield
    await app.state.db_pool.close()


app = FastAPI(
    title='PA Compact Licensing API',
    description='APIs supporting the PA Compact Commission Data System',
    docs_url='/docs',
    lifespan=lifespan,
)

app.include_router(router)

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=settings.api_port, log_level=settings.log_level.lower())
