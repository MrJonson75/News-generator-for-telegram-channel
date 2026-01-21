from fastapi import APIRouter, Depends, HTTPException, status
from app.api.schemas import NewsItemSchema
from app.database import test_connection, get_session
from app.ai.openai_client import openai_client



router = APIRouter(
    prefix="/api",
    tags=["api"],
)



@router.get("/health")
async def health():
    result = await test_connection()
    openai_status = await openai_client.health_client()
    return {
        "status": "ok",
        "database": result,
        "openai": openai_status
    }


@router.get("/sources")
async def get_sources():
    return {"message": "ok"}


@router.get("/keywords")
async def get_keywords():
    return {"message": "ok"}


# @router.get("/posts", response_model=List[Post], status_code=status.HTTP_200_OK)
# async def get_posts() -> List[Post]:
#     pass
#
#
#
# @router.post("/generate")
# async def generate_post(news_item: NewsItem):
#     return {"message": "ok"}

