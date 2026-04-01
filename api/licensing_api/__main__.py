import uvicorn
from fastapi import FastAPI

from licensing_api.config import settings
from licensing_api.routes.health import router

app = FastAPI(
    title='PA Compact Licensing API',
    description='APIs supporting the PA Compact Commission Data System',
    docs_url='/docs',
)

app.include_router(router)

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=settings.api_port, log_level=settings.log_level.lower())
