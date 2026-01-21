from fastapi import FastAPI
from app.config import settings, APP_META
from app.api.sources import router as sources_router
from app.database import test_connection
from app.ai.openai_client import openai_client
from app.logger import logger

app = FastAPI(
    title=APP_META.name,
    description=APP_META.description,
    version=APP_META.version,
    contact={
        "name": APP_META.contact.name,
        "email": APP_META.contact.email,
        "url": APP_META.contact.url
    }
)

app.include_router(
    sources_router,
)


@app.get("/")
async def root():
    return {"message": "генератор новостей"}


@app.get("/health")
async def health():
    logger.info("health check")
    result = await test_connection()
    openai_status = await openai_client.health_client()
    logger.info(f"openai status: {openai_status}, database status: {result}")
    return {
        "status": "ok",
        "database": result,
        "openai": openai_status
    }


