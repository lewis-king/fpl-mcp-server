from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class Player(BaseModel):
    id: int
    web_name: str
    first_name: str
    second_name: str
    team: int
    element_type: int
    now_cost: int
    form: str
    points_per_game: str
    news: str
    
    # Computed fields
    team_name: Optional[str] = None
    position: Optional[str] = None
    price: float = Field(default=0.0)

    def __init__(self, **data):
        super().__init__(**data)
        self.price = self.now_cost / 10

class TransferPayload(BaseModel):
    chip: Optional[str] = None
    entry: int
    event: int
    transfers: List[Dict[str, int]] 
    wildcard: bool = False
    freehit: bool = False