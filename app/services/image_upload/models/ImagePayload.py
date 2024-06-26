from typing import Optional
from pydantic import BaseModel

class ImagePayload(BaseModel):
    item_id: Optional[int]
    item_name: str
    quantity: int