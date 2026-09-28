from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.note_agent import NoteAgent
from app.core.config import get_settings
from app.db.session import get_db
from app.models.account import Role
from app.services.auth import CurrentAccount
from app.schemas.note import NoteCreate, NoteProcessResponse
from app.services.note_processing import NoteProcessingService

router = APIRouter(prefix="/notes", tags=["notes"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


def get_note_agent() -> NoteAgent:
    return NoteAgent(get_settings())


NoteAgentDependency = Annotated[NoteAgent, Depends(get_note_agent)]


@router.post(
    "/process",
    response_model=NoteProcessResponse,
    status_code=status.HTTP_201_CREATED,
)
async def process_note(
    payload: NoteCreate,
    account: CurrentAccount,
    db: DbSession,
    agent: NoteAgentDependency,
) -> NoteProcessResponse:
    patient_id = account.patient_id if account.role == Role.PATIENT else payload.patient_id
    if patient_id is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Choose which patient this note is for.")
    return await NoteProcessingService(db, agent).process(payload.text, patient_id)
