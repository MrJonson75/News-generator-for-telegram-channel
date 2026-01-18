from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from app.api.schemas import NewsItem, Post, Keyword, Source



router = APIRouter(
    prefix="/api",
    tags=["api"],
)



@router.get("/health")
async def health():
    return {"status": "ok"}


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

