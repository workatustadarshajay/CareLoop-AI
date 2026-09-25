from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.agents.note_agent import AgentConfigurationError
from app.api.routes.cards import router as cards_router
from app.api.routes.notes import router as notes_router
from app.core.config import get_settings
from app.db.session import engine


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    yield
    await engine.dispose()


settings = get_settings()
app = FastAPI(title="CareLoop AI", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.exception_handler(AgentConfigurationError)
async def handle_agent_configuration_error(
    _: Request,
    error: AgentConfigurationError,
) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": str(error)})


app.include_router(notes_router, prefix="/api")
app.include_router(cards_router, prefix="/api")
