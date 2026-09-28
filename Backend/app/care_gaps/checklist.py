from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field

from app.models.card import CardType

CHECKLIST_PATH = Path(__file__).with_name("checklist.json")


class ExpectedItem(BaseModel):
    label: str
    card_type: CardType
    card_description: str


class Diagnosis(BaseModel):
    name: str
    aliases: list[str] = Field(min_length=1)
    expected_items: list[ExpectedItem] = Field(min_length=1)


class Checklist(BaseModel):
    diagnoses: list[Diagnosis]


@lru_cache
def load_checklist() -> Checklist:
    return Checklist.model_validate_json(CHECKLIST_PATH.read_text(encoding="utf-8"))
