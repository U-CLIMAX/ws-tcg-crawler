from typing import List

from pydantic import BaseModel, Field


class CardVersion(BaseModel):
    """同一張卡片的不同版本 (例如不同罕貴度)"""

    id: str
    rarity: str


class CardData(BaseModel):
    """卡片主要資料結構"""

    key: str = Field(exclude=True)  # 用於去重的 Key，不寫入 JSON
    name: str
    product_name: str
    type: str
    level: int | str
    power: int | str
    cost: int | str
    soul: int | str
    trigger_soul_count: int
    trait: List[str] | str
    color: str
    effect: str
    image_url: str = Field(exclude=True)  # 只用於下載，不寫入 JSON

    # 用於儲存該卡片的所有版本 (RR, SP 等)
    all_cards: List[CardVersion] = []

    class Config:
        populate_by_name = True
