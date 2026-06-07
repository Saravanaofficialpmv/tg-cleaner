"""
Session management helpers.
Generates secure session IDs and retrieves session records.
"""

import secrets
import hashlib
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.models import UserSession


def generate_session_id() -> str:
    """Generate a cryptographically secure session ID."""
    return secrets.token_urlsafe(32)


async def create_user_session(
    db: AsyncSession,
    phone: str,
    session_string: str,
    api_id: Optional[int] = None,
    api_hash: Optional[str] = None,
) -> UserSession:
    """Create and persist a new user session."""
    session_id = generate_session_id()
    user_session = UserSession(
        session_id=session_id,
        phone=phone,
        session_string=session_string,
        api_id=api_id,
        api_hash=api_hash,
        is_active=True,
    )
    db.add(user_session)
    await db.flush()
    return user_session


async def get_user_session(db: AsyncSession, session_id: str) -> Optional[UserSession]:
    """Retrieve an active session by ID."""
    result = await db.execute(
        select(UserSession).where(
            UserSession.session_id == session_id,
            UserSession.is_active == True,
        )
    )
    return result.scalar_one_or_none()


async def deactivate_session(db: AsyncSession, session_id: str) -> bool:
    """Mark a session as inactive (logout)."""
    result = await db.execute(
        select(UserSession).where(UserSession.session_id == session_id)
    )
    session = result.scalar_one_or_none()
    if session:
        session.is_active = False
        return True
    return False


async def update_session_string(db: AsyncSession, session_id: str, session_string: str):
    """Update the Telethon session string after sign-in."""
    result = await db.execute(
        select(UserSession).where(UserSession.session_id == session_id)
    )
    session = result.scalar_one_or_none()
    if session:
        session.session_string = session_string
