from pydantic import BaseModel, ConfigDict, Field

from app.schemas.card import CardRead


class NoteCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    text: str = Field(min_length=1, max_length=12_000)


class NoteProcessResponse(BaseModel):
    note_id: int
    cards: list[CardRead]
