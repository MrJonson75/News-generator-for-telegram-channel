from fastapi import FastAPI
from app.config import settings, APP_META
from app.api.endpoints import router as endpoints_router


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

app.include_router(endpoints_router)


@app.get("/")
async def root():
    return {"message": "Hello World"}
