"""
Cleanup routes: Server-Sent Events stream for real-time progress.
Handles leaving groups/channels with rate-limit safety.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.database import get_db, AsyncSessionLocal
from app.services import telegram as tg_service
from app.services import session as sess_service
from app.models.models import ChatRecord, CleanupLog

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/cleanup", tags=["cleanup"])

# In-memory stop flags (session_id -> bool)
_stop_flags: dict = {}


class PreviewRequest(BaseModel):
    session_id: str


@router.post("/preview")
async def preview_cleanup(
    body: PreviewRequest,
    db: AsyncSession = Depends(get_db),
):
    """Return a preview of what will be left vs kept."""
    session = await sess_service.get_user_session(db=db, session_id=body.session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Session not found.")

    result = await db.execute(
        select(ChatRecord).where(ChatRecord.session_id == body.session_id)
    )
    all_chats = result.scalars().all()

    to_leave = [c for c in all_chats if not c.is_kept]
    to_keep = [c for c in all_chats if c.is_kept]

    return {
        "total": len(all_chats),
        "to_leave": len(to_leave),
        "to_keep": len(to_keep),
        "leave_list": [
            {"chat_id": c.chat_id, "name": c.name, "chat_type": c.chat_type}
            for c in to_leave
        ],
    }


@router.get("/stream")
async def cleanup_stream(
    session_id: str = Query(...),
    delay: float = Query(2.0, ge=0.5, le=30.0),
):
    """
    Server-Sent Events endpoint.
    Streams cleanup progress in real-time.
    """
    _stop_flags[session_id] = False

    async def event_generator() -> AsyncGenerator[str, None]:
        async with AsyncSessionLocal() as db:
            try:
                # Validate session
                session = await sess_service.get_user_session(db=db, session_id=session_id)
                if not session:
                    yield _sse({"type": "error", "message": "Session not found."})
                    return

                # Get client
                try:
                    client = await tg_service.get_client_for_session(session_id, db)
                except Exception as e:
                    logger.warning(f"Failed to restore Telegram client: {e}")
                    yield _sse({"type": "error", "message": "Telegram client not connected."})
                    return

                # Clear previous cleanup logs so we only show the status of the current run
                await db.execute(
                    delete(CleanupLog).where(CleanupLog.session_id == session_id)
                )
                await db.commit()

                # Get chats to leave
                result = await db.execute(
                    select(ChatRecord).where(
                        ChatRecord.session_id == session_id,
                        ChatRecord.is_kept == False,
                    )
                )
                to_leave = result.scalars().all()
                total = len(to_leave)

                if total == 0:
                    yield _sse({"type": "done", "message": "No chats to leave.", "total": 0, "success": 0, "failed": 0})
                    return

                yield _sse({"type": "start", "total": total})

                success_count = 0
                failed_count = 0

                for idx, chat in enumerate(to_leave, 1):
                    # Check stop flag
                    if _stop_flags.get(session_id):
                        yield _sse({
                            "type": "stopped",
                            "message": "Cleanup stopped by user.",
                            "processed": idx - 1,
                            "success": success_count,
                            "failed": failed_count,
                        })
                        break

                    yield _sse({
                        "type": "progress",
                        "current": idx,
                        "total": total,
                        "chat_name": chat.name,
                        "chat_type": chat.chat_type,
                        "status": "leaving",
                    })

                    # Attempt to leave
                    action = "failed"
                    error_msg = None
                    try:
                        await tg_service.leave_chat(client, chat.chat_id)
                        action = "left"
                        success_count += 1
                        yield _sse({
                            "type": "progress",
                            "current": idx,
                            "total": total,
                            "chat_name": chat.name,
                            "chat_type": chat.chat_type,
                            "status": "left",
                        })
                    except Exception as e:
                        failed_count += 1
                        error_msg = str(e)
                        yield _sse({
                            "type": "progress",
                            "current": idx,
                            "total": total,
                            "chat_name": chat.name,
                            "chat_type": chat.chat_type,
                            "status": "failed",
                            "error": error_msg,
                        })

                    # Log to DB
                    log = CleanupLog(
                        session_id=session_id,
                        chat_id=chat.chat_id,
                        chat_name=chat.name,
                        action=action,
                        error_message=error_msg,
                    )
                    db.add(log)

                    # Delete from cache if left successfully
                    if action == "left":
                        await db.delete(chat)

                    # Rate-limit safe delay
                    await asyncio.sleep(delay)

                await db.commit()
                yield _sse({
                    "type": "done",
                    "message": "Cleanup complete.",
                    "total": total,
                    "success": success_count,
                    "failed": failed_count,
                })

            except Exception as e:
                logger.exception("Cleanup stream error")
                yield _sse({"type": "error", "message": str(e)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post("/stop")
async def stop_cleanup(body: dict):
    """Signal the cleanup stream to stop after the current operation."""
    session_id = body.get("session_id")
    if session_id:
        _stop_flags[session_id] = True
    return {"message": "Stop signal sent."}


@router.get("/logs")
async def get_cleanup_logs(
    session_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve cleanup history for the current session."""
    result = await db.execute(
        select(CleanupLog)
        .where(CleanupLog.session_id == session_id)
        .order_by(CleanupLog.performed_at.desc())
    )
    logs = result.scalars().all()
    return {
        "logs": [
            {
                "chat_name": log.chat_name,
                "action": log.action,
                "error_message": log.error_message,
                "performed_at": log.performed_at.isoformat() if log.performed_at else None,
            }
            for log in logs
        ]
    }


class LeaveSingleRequest(BaseModel):
    session_id: str
    chat_id: int


@router.post("/leave-single")
async def leave_single_chat(
    body: LeaveSingleRequest,
    db: AsyncSession = Depends(get_db),
):
    """Leave a single group or channel immediately."""
    session = await sess_service.get_user_session(db=db, session_id=body.session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Session not found.")

    try:
        client = await tg_service.get_client_for_session(body.session_id, db)
    except Exception as e:
        logger.warning(f"Failed to restore Telegram client: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Telegram client not connected. Please log in again. Error: {str(e)}"
        )

    # Find the chat record in DB cache
    result = await db.execute(
        select(ChatRecord).where(
            ChatRecord.session_id == body.session_id,
            ChatRecord.chat_id == body.chat_id,
        )
    )
    chat = result.scalars().first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found in database cache.")

    # Attempt to leave
    try:
        success = await tg_service.leave_chat(client, body.chat_id)
        if not success:
            raise HTTPException(status_code=429, detail="FloodWait error: Telegram requested wait.")
    except Exception as e:
        logger.error(f"Error leaving single chat {body.chat_id}: {e}")
        # Log failure
        log = CleanupLog(
            session_id=body.session_id,
            chat_id=body.chat_id,
            chat_name=chat.name,
            action="failed",
            error_message=str(e),
        )
        db.add(log)
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Failed to leave chat: {str(e)}")

    # Log success
    log = CleanupLog(
        session_id=body.session_id,
        chat_id=body.chat_id,
        chat_name=chat.name,
        action="left",
    )
    db.add(log)

    # Delete from local cache so it disappears instantly
    await db.delete(chat)
    await db.commit()

    return {"status": "success", "message": f"Successfully left {chat.name}."}


def _sse(data: dict) -> str:
    """Format a dict as an SSE data line."""
    return f"data: {json.dumps(data)}\n\n"

