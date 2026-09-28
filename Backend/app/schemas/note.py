from pydantic import BaseModel, ConfigDict, Field

from app.schemas.card import CardRead


class NoteCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    text: str = Field(min_length=1, max_length=12_000)
    # Doctors choose the patient; for patient logins this is ignored and their own id is used.
    patient_id: int | None = None


class NoteProcessResponse(BaseModel):
    note_id: int
    cards: list[CardRead]
    closed_card_ids: list[int] = []
