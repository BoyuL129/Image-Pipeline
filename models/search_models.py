from pydantic import BaseModel
from typing import Optional

class SearchRequest(BaseModel):
    image_url: str
    description: Optional[str] = None

class SearchResult(BaseModel):
    title: str
    link: str
    image: str
