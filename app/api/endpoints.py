from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from app.api.schemas import NewsItem, Post, Keyword, Source
from app.database import test_connection, get_session



router = APIRouter(
    prefix="/api",
    tags=["api"],
)



@router.get("/health")
async def health():
    result = await test_connection()
    return {
        "status": "ok",
        "database": result
    }


@router.get("/sources")
async def get_sources():
    return {"message": "ok"}


@router.get("/keywords")
async def get_keywords():
    return {"message": "ok"}


@router.get("/posts", response_model=List[Post], status_code=status.HTTP_200_OK)
async def get_posts() -> List[Post]:
    pass



@router.post("/generate")
async def generate_post(news_item: NewsItem):
    return {"message": "ok"}

