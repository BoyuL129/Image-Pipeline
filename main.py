import os
from typing import Union
from fastapi import FastAPI, HTTPException
from models.search_models import SearchRequest, SearchResult
from services.image_service import ImageService
from services.search_service import SearchService
from services.matching_service import MatchingService

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.post("/search", response_model=SearchResult)
def reverse_search(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}