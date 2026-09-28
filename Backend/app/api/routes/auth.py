from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.account import Account, Patient, Role
from app.services.auth import AdminAccount, CurrentAccount, DoctorAccount, hash_password, login

router = APIRouter(tags=["auth"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


class LoginRequest(BaseModel):
    username: str
    password: str


class AccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    username: str
    role: Role
    patient_id: int | None
    token: str


class PatientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    username: str | None = None


class PatientCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=200)
    username: str = Field(min_length=2, max_length=100, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=6, max_length=200)


@router.post("/auth/login", response_model=AccountRead)
async def login_route(payload: LoginRequest, db: DbSession) -> Account:
    account = await login(db, payload.username, payload.password)
    if account is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong username or password.")
    return account


@router.get("/auth/me", response_model=AccountRead)
async def me(account: CurrentAccount) -> Account:
    return account


@router.get("/patients", response_model=list[PatientRead])
async def list_patients(_: DoctorAccount, db: DbSession) -> list[PatientRead]:
    rows = await db.execute(
        select(Patient, Account.username)
        .outerjoin(Account, (Account.patient_id == Patient.id) & (Account.role == Role.PATIENT))
        .order_by(Patient.name)
    )
    return [PatientRead(id=p.id, name=p.name, username=username) for p, username in rows.all()]


@router.post("/patients", response_model=PatientRead, status_code=status.HTTP_201_CREATED)
async def create_patient(payload: PatientCreate, _: AdminAccount, db: DbSession) -> PatientRead:
    """Administrators only: create a patient together with their login."""
    taken = await db.execute(select(Account.id).where(Account.username == payload.username))
    if taken.scalar_one_or_none() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "That username is already taken.")
    patient = Patient(name=payload.name)
    db.add(patient)
    await db.flush()
    db.add(Account(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=Role.PATIENT,
        patient_id=patient.id,
    ))
    await db.commit()
    return PatientRead(id=patient.id, name=patient.name, username=payload.username)
