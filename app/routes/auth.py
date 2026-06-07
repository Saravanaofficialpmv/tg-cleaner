"""
Authentication routes: login, OTP verification, logout.
"""

import logging
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services import telegram as tg_service
from app.services import session as sess_service
from app.models.models import UserSession

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

# ── Pydantic request schemas ──────────────────────────────────────────────────

class StartLoginRequest(BaseModel):
    api_id: int
    api_hash: str
    phone: str


class VerifyOtpRequest(BaseModel):
    session_id: str
    code: str
    password: Optional[str] = None


class LogoutRequest(BaseModel):
    session_id: str


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/start")
async def start_login(
    body: StartLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Step 1: Send OTP to the user's phone via Telegram.
    Creates a temporary pending-auth entry.
    """
    # Create a temporary session placeholder
    temp_session_id = sess_service.generate_session_id()

    try:
        result = await tg_service.send_code(
            session_id=temp_session_id,
            api_id=body.api_id,
            api_hash=body.api_hash,
            phone=body.phone,
        )
    except Exception as e:
        logger.error(f"Error sending code: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    # Persist a placeholder session to DB so we can track it
    user_session = await sess_service.create_user_session(
        db=db,
        phone=body.phone,
        session_string="",
        api_id=body.api_id,
        api_hash=body.api_hash,
    )
    # Override the random ID with our temp_session_id
    user_session.session_id = temp_session_id
    await db.flush()

    return {
        "session_id": temp_session_id,
        "phone": body.phone,
        "message": "OTP sent successfully.",
    }


@router.post("/verify")
async def verify_otp(
    body: VerifyOtpRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Step 2: Verify OTP and complete sign-in.
    Returns a live session_id the frontend stores in localStorage.
    """
    try:
        auth_result = await tg_service.sign_in(
            session_id=body.session_id,
            code=body.code.strip(),
            password=body.password,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Sign-in error: {e}")
        raise HTTPException(status_code=500, detail="Authentication failed. Please try again.")

    # Get session details to return to the client for stateless auto-healing
    session = await sess_service.get_user_session(db=db, session_id=body.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session placeholder not found.")

    # Persist the real session string
    await sess_service.update_session_string(
        db=db,
        session_id=body.session_id,
        session_string=auth_result["session_string"],
    )

    return {
        "session_id": body.session_id,
        "session_string": auth_result["session_string"],
        "api_id": session.api_id,
        "api_hash": session.api_hash,
        "phone": session.phone,
        "user": {
            "first_name": auth_result.get("first_name", ""),
            "username": auth_result.get("username", ""),
        },
        "message": "Logged in successfully.",
    }


@router.post("/logout")
async def logout(
    body: LogoutRequest,
    db: AsyncSession = Depends(get_db),
):
    """Disconnect client and invalidate session."""
    await tg_service.disconnect_client(body.session_id)
    await sess_service.deactivate_session(db=db, session_id=body.session_id)
    return {"message": "Logged out successfully."}


@router.get("/status/{session_id}")
async def check_status(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Check whether a session is still active."""
    session = await sess_service.get_user_session(db=db, session_id=session_id)
    if not session:
        return {"active": False}
    return {"active": True, "phone": session.phone}
