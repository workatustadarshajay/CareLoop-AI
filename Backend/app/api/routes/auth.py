from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.account import Account, Patient, Role
from app.models.card import Card
from app.models.note import Note
from app.services.auth import (
    AdminAccount,
    CareTeamAccount,
    CurrentAccount,
    hash_password,
    login,
)

router = APIRouter(tags=["auth"])

DbSession = Annotated[AsyncSession, Depends(get_db)]

USERNAME_PATTERN = r"^[A-Za-z0-9_.-]+$"
DUPLICATE_USERNAME = "That username is already taken."


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
    username: str = Field(min_length=2, max_length=100, pattern=USERNAME_PATTERN)
    password: str = Field(min_length=6, max_length=200)


class AccountListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: Role
    patient_id: int | None = None
    patient_name: str | None = None


class AccountCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    username: str = Field(min_length=2, max_length=100, pattern=USERNAME_PATTERN)
    password: str = Field(min_length=6, max_length=200)
    role: Role
    # Only patient accounts carry a name; it becomes the patient record.
    name: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def patient_accounts_need_a_name(self) -> "AccountCreate":
        if self.role == Role.PATIENT and not (self.name or "").strip():
            raise ValueError("A patient account needs the patient's name.")
        return self


class AccountUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    username: str | None = Field(default=None, min_length=2, max_length=100, pattern=USERNAME_PATTERN)
    password: str | None = Field(default=None, min_length=6, max_length=200)
    role: Role | None = None
    name: str | None = Field(default=None, max_length=200)


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
async def list_patients(_: CareTeamAccount, db: DbSession) -> list[PatientRead]:
    """Care coordinators, doctors and admins use this to pick the patient they are working on."""
    rows = await db.execute(
        select(Patient, Account.username)
        .outerjoin(Account, (Account.patient_id == Patient.id) & (Account.role == Role.PATIENT))
        .order_by(Patient.name)
    )
    return [PatientRead(id=p.id, name=p.name, username=username) for p, username in rows.all()]


async def _create_account(
    db: AsyncSession,
    *,
    role: Role,
    username: str,
    password: str,
    name: str | None = None,
) -> AccountListItem:
    taken = await db.execute(select(Account.id).where(Account.username == username))
    if taken.scalar_one_or_none() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, DUPLICATE_USERNAME)

    patient_name: str | None = None
    patient_id: int | None = None
    if role == Role.PATIENT:
        patient = Patient(name=(name or "").strip())
        db.add(patient)
        await db.flush()
        patient_id, patient_name = patient.id, patient.name

    account = Account(
        username=username,
        password_hash=hash_password(password),
        role=role,
        patient_id=patient_id,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return AccountListItem(
        id=account.id,
        username=account.username,
        role=account.role,
        patient_id=patient_id,
        patient_name=patient_name,
    )


@router.post("/patients", response_model=PatientRead, status_code=status.HTTP_201_CREATED)
async def create_patient(payload: PatientCreate, _: AdminAccount, db: DbSession) -> PatientRead:
    """Administrators only: create a patient together with their login.

    Kept as a patient-only convenience alias of ``POST /accounts``.
    """
    created = await _create_account(
        db, role=Role.PATIENT, username=payload.username, password=payload.password, name=payload.name
    )
    return PatientRead(id=created.patient_id or 0, name=created.patient_name or payload.name, username=created.username)


async def _account_item(db: AsyncSession, account: Account) -> AccountListItem:
    patient_name = None
    if account.patient_id is not None:
        patient = await db.get(Patient, account.patient_id)
        patient_name = patient.name if patient else None
    return AccountListItem(
        id=account.id,
        username=account.username,
        role=account.role,
        patient_id=account.patient_id,
        patient_name=patient_name,
    )


@router.get("/accounts", response_model=list[AccountListItem])
async def list_accounts(_: AdminAccount, db: DbSession) -> list[AccountListItem]:
    """Administrators only: every login, including who each patient account belongs to."""
    rows = await db.execute(
        select(Account, Patient.name)
        .outerjoin(Patient, Patient.id == Account.patient_id)
        .order_by(Account.role, Account.username)
    )
    return [
        AccountListItem(
            id=account.id,
            username=account.username,
            role=account.role,
            patient_id=account.patient_id,
            patient_name=patient_name,
        )
        for account, patient_name in rows.all()
    ]


@router.post("/accounts", response_model=AccountListItem, status_code=status.HTTP_201_CREATED)
async def create_account(payload: AccountCreate, _: AdminAccount, db: DbSession) -> AccountListItem:
    """Administrators only: add a patient, doctor, care coordinator or administrator login."""
    return await _create_account(
        db, role=payload.role, username=payload.username, password=payload.password, name=payload.name
    )


async def _other_admins(db: AsyncSession, account_id: int) -> int:
    rows = await db.execute(
        select(func.count()).select_from(Account).where(Account.role == Role.ADMIN, Account.id != account_id)
    )
    return rows.scalar_one()


@router.patch("/accounts/{account_id}", response_model=AccountListItem)
async def update_account(
    account_id: int,
    payload: AccountUpdate,
    admin: AdminAccount,
    db: DbSession,
) -> AccountListItem:
    """Administrators only: rename a login, reset its password, rename the patient, or change a staff role."""
    account = await db.get(Account, account_id)
    if account is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Account not found.")

    if payload.username is not None and payload.username != account.username:
        taken = await db.execute(
            select(Account.id).where(Account.username == payload.username, Account.id != account.id)
        )
        if taken.scalar_one_or_none() is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, DUPLICATE_USERNAME)
        account.username = payload.username

    if payload.password is not None:
        account.password_hash = hash_password(payload.password)
        # The old token was issued for the old password; force a fresh sign-in.
        account.token = None

    if payload.name is not None:
        if account.patient_id is None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                "Only patient accounts carry a patient name.",
            )
        patient = await db.get(Patient, account.patient_id)
        if patient is not None:
            patient.name = payload.name

    if payload.role is not None and payload.role != account.role:
        if account.id == admin.id:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, "You cannot change the role of the account you are signed in with."
            )
        if account.patient_id is not None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                "A patient login keeps the patient role. Delete it instead when the patient no longer needs access.",
            )
        if account.role == Role.ADMIN and await _other_admins(db, account.id) == 0:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "At least one administrator account must remain.")
        account.role = payload.role

    await db.commit()
    await db.refresh(account)
    return await _account_item(db, account)


@router.delete("/accounts/{account_id}")
async def delete_account(account_id: int, admin: AdminAccount, db: DbSession) -> dict:
    """Administrators only. A patient account takes the patient, their logins and their cards with it."""
    account = await db.get(Account, account_id)
    if account is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Account not found.")
    if account.id == admin.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "You cannot delete the account you are signed in with."
        )

    removed = {"patient": None, "notes": 0, "cards": 0}
    if account.patient_id is not None:
        if await _other_admins(db, account.id) == 0 and account.role == Role.ADMIN:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "At least one administrator account must remain.")
        patient = await db.get(Patient, account.patient_id)
        removed["patient"] = patient.name if patient else None
        counted = await db.execute(
            select(
                func.count(func.distinct(Note.id)),
                func.count(Card.id),
            )
            .select_from(Note)
            .outerjoin(Card, Card.note_id == Note.id)
            .where(Note.patient_id == account.patient_id)
        )
        notes, cards = counted.one()
        removed["notes"], removed["cards"] = int(notes or 0), int(cards or 0)
        # Notes carry the patient's cards; reminders, dependencies and review flags cascade from them.
        await db.execute(delete(Note).where(Note.patient_id == account.patient_id))
        await db.execute(delete(Patient).where(Patient.id == account.patient_id))

    await db.execute(delete(Account).where(Account.id == account.id))
    await db.commit()

    if removed["patient"] is not None:
        return {
            "success": True,
            "message": (
                f"Deleted {removed['patient']}: their login, {removed['notes']} note(s) "
                f"and {removed['cards']} card(s)."
            ),
        }
    return {"success": True, "message": f"Deleted the {account.role.replace('_', ' ')} login “{account.username}”."}
