import uvicorn
from fastapi import FastAPI
from app.config import settings



app = FastAPI(
    title=settings.app_name,
    description=settings.description,
    version=settings.version,
    contact={
        "email": settings.contact["email"],
        "url": settings.contact["url"],
        "name": settings.contact["name"],
    }
)



@app.get("/")
async def root():
    return {"message": "Hello World"}



if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)