import os
from typing import Union
from fastapi import FastAPI, HTTPException
from models.search_models import SearchRequest, SearchResult
from 

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.post("/search", response_model=SearchResult)
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}