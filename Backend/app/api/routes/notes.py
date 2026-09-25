from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.note_agent import NoteAgent
from app.core.config import get_settings
from app.db.session import get_db
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
    db: DbSession,
    agent: NoteAgentDependency,
) -> NoteProcessResponse:
    return await NoteProcessingService(db, agent).process(payload.text)
