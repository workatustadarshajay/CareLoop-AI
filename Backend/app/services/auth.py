import hashlib
import secrets
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.models.account import Account, Role


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(8)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
    return f"{salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    salt, _ = stored.split("$", 1)
    return secrets.compare_digest(hash_password(password, salt), stored)


async def login(db: AsyncSession, username: str, password: str) -> Account | None:
    account = (await db.execute(select(Account).where(Account.username == username))).scalar_one_or_none()
    if account is None or not verify_password(password, account.password_hash):
        return None
    account.token = secrets.token_urlsafe(32)
    await db.commit()
    return account


async def current_account(authorization: Annotated[str | None, Header()] = None) -> Account:
    scheme, _, token = (authorization or "").partition(" ")
    account = None
    if scheme.lower() == "bearer" and token:
        # Own session: the request session must stay transaction-free for services that call begin().
        async with async_session_factory() as db:
            account = (await db.execute(select(Account).where(Account.token == token))).scalar_one_or_none()
    if account is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Login required.")
    return account


CurrentAccount = Annotated[Account, Depends(current_account)]


async def doctor_account(account: CurrentAccount) -> Account:
    if account.role not in (Role.DOCTOR, Role.ADMIN):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Doctor/admin access required.")
    return account


async def admin_account(account: CurrentAccount) -> Account:
    if account.role != Role.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Administrator access required.")
    return account


DoctorAccount = Annotated[Account, Depends(doctor_account)]
AdminAccount = Annotated[Account, Depends(admin_account)]
