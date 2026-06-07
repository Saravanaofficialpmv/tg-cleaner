"""
Telegram service layer using Telethon.
Handles authentication, fetching chats, and leaving groups/channels.
"""

import asyncio
import os
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from telethon import TelegramClient, errors
from telethon.sessions import StringSession
from telethon.tl.types import (
    Channel, Chat, ChatForbidden, ChannelForbidden,
    InputNotifyPeer, InputPeerNotifySettings,
    DialogFilter, User
)
from telethon.tl.functions.channels import LeaveChannelRequest
from telethon.tl.functions.messages import (
    DeleteChatUserRequest, GetPeerDialogsRequest
)

logger = logging.getLogger(__name__)

# In-memory store for active clients (keyed by session_id)
_active_clients: Dict[str, TelegramClient] = {}
# Store pending OTP phone codes (keyed by session_id)
_pending_auth: Dict[str, Dict[str, Any]] = {}


async def create_client(api_id: int, api_hash: str, session_string: Optional[str] = None) -> TelegramClient:
    """Create and connect a Telethon client."""
    session = StringSession(session_string) if session_string else StringSession()
    client = TelegramClient(session, api_id, api_hash)
    await client.connect()
    return client


async def send_code(session_id: str, api_id: int, api_hash: str, phone: str) -> Dict[str, Any]:
    """
    Send OTP to the given phone number.
    Returns a dict with 'phone_code_hash'.
    """
    client = await create_client(api_id, api_hash)
    result = await client.send_code_request(phone)
    # Store client + metadata for the sign_in step
    _pending_auth[session_id] = {
        "client": client,
        "api_id": api_id,
        "api_hash": api_hash,
        "phone": phone,
        "phone_code_hash": result.phone_code_hash,
    }
    return {"phone_code_hash": result.phone_code_hash}


async def sign_in(session_id: str, code: str, password: Optional[str] = None) -> Dict[str, Any]:
    """
    Complete sign-in with the received OTP code.
    Returns session string on success.
    """
    if session_id not in _pending_auth:
        raise ValueError("No pending auth found. Please restart login.")

    auth = _pending_auth[session_id]
    client: TelegramClient = auth["client"]

    try:
        user = await client.sign_in(
            phone=auth["phone"],
            code=code,
            phone_code_hash=auth["phone_code_hash"],
        )
    except errors.SessionPasswordNeededError:
        if not password:
            raise ValueError("Two-factor authentication required. Please provide your password.")
        user = await client.sign_in(password=password)
    except errors.PhoneCodeInvalidError:
        raise ValueError("Invalid code. Please try again.")
    except errors.PhoneCodeExpiredError:
        raise ValueError("Code expired. Please request a new one.")

    session_string = client.session.save()
    _active_clients[session_id] = client
    del _pending_auth[session_id]

    return {
        "session_string": session_string,
        "user_id": user.id,
        "username": user.username or "",
        "first_name": user.first_name or "",
    }


async def get_or_restore_client(session_id: str, api_id: int, api_hash: str, session_string: str) -> TelegramClient:
    """Get cached client or restore it from session string."""
    if session_id in _active_clients:
        client = _active_clients[session_id]
        if client.is_connected():
            return client

    client = await create_client(api_id, api_hash, session_string)
    if not await client.is_user_authorized():
        raise ValueError("Session expired. Please log in again.")
    _active_clients[session_id] = client
    return client


async def disconnect_client(session_id: str):
    """Disconnect and remove a client."""
    if session_id in _active_clients:
        try:
            await _active_clients[session_id].disconnect()
        except Exception:
            pass
        del _active_clients[session_id]
    _pending_auth.pop(session_id, None)


async def fetch_dialogs(client: TelegramClient) -> List[Dict[str, Any]]:
    """
    Fetch all groups, channels, supergroups from the account.
    Returns a list of chat dicts.
    """
    chats = []

    async for dialog in client.iter_dialogs():
        entity = dialog.entity

        if isinstance(entity, (ChatForbidden, ChannelForbidden)):
            continue

        chat_type = _get_chat_type(entity)
        if not chat_type:
            continue

        # Safely get member count
        member_count = None
        if hasattr(entity, "participants_count") and entity.participants_count:
            member_count = entity.participants_count
        elif isinstance(entity, Chat) and hasattr(entity, "participants_count"):
            member_count = entity.participants_count

        # Last activity from dialog message
        last_activity = None
        if dialog.message and dialog.message.date:
            last_activity = dialog.message.date.isoformat()

        # Check mute status
        is_muted = False
        if dialog.dialog and dialog.dialog.notify_settings:
            ns = dialog.dialog.notify_settings
            if hasattr(ns, "mute_until") and ns.mute_until:
                try:
                    mute_until = ns.mute_until
                    if isinstance(mute_until, datetime):
                        is_muted = mute_until > datetime.now(timezone.utc)
                    elif isinstance(mute_until, int):
                        is_muted = mute_until > datetime.now(timezone.utc).timestamp()
                except Exception:
                    pass
            elif hasattr(ns, "silent") and ns.silent:
                is_muted = True

        # Check archived
        is_archived = bool(dialog.archived)

        chats.append({
            "chat_id": entity.id,
            "name": dialog.name or "Unknown",
            "chat_type": chat_type,
            "username": getattr(entity, "username", None),
            "member_count": member_count,
            "unread_count": dialog.unread_count or 0,
            "is_muted": is_muted,
            "is_archived": is_archived,
            "last_activity": last_activity,
        })

    return chats


def _get_chat_type(entity) -> Optional[str]:
    """Determine the chat type string."""
    if isinstance(entity, Chat):
        return "group"
    if isinstance(entity, Channel):
        if entity.megagroup or entity.gigagroup:
            return "supergroup"
        if entity.broadcast:
            return "channel"
        return "supergroup"
    if isinstance(entity, User):
        if entity.bot:
            return "bot"
        return "user"
    return None


async def leave_chat(client: TelegramClient, chat_id: int) -> bool:
    """
    Leave a group/channel or stop/block a bot. Returns True on success.
    """
    try:
        entity = await client.get_entity(chat_id)
        if isinstance(entity, Channel):
            await client(LeaveChannelRequest(entity))
        elif isinstance(entity, Chat):
            me = await client.get_me()
            await client(DeleteChatUserRequest(chat_id=chat_id, user_id=me))
        elif isinstance(entity, User):
            if entity.bot:
                # Stop & block the bot
                from telethon.tl.functions.contacts import BlockRequest
                try:
                    await client(BlockRequest(id=entity))
                except Exception as e:
                    logger.warning(f"Could not block bot {chat_id}: {e}")
            await client.delete_dialog(entity)
        return True
    except errors.FloodWaitError as e:
        logger.warning(f"FloodWait: sleeping {e.seconds}s")
        await asyncio.sleep(e.seconds)
        return False
    except Exception as e:
        logger.error(f"Error leaving chat/bot {chat_id}: {e}")
        raise


async def download_photo(client: TelegramClient, entity, save_dir: str) -> Optional[str]:
    """Download profile photo and return relative path."""
    try:
        os.makedirs(save_dir, exist_ok=True)
        path = await client.download_profile_photo(entity, file=save_dir)
        if path:
            return os.path.relpath(path, start=".")
    except Exception as e:
        logger.debug(f"Could not download photo: {e}")
    return None


async def get_client_for_session(session_id: str, db: AsyncSession) -> TelegramClient:
    """Get connected TelegramClient for session, restoring from DB if needed."""
    if session_id in _active_clients:
        client = _active_clients[session_id]
        if client.is_connected():
            return client

    # Retrieve session from DB
    from app.services import session as sess_service
    session = await sess_service.get_user_session(db=db, session_id=session_id)
    if not session or not session.session_string:
        raise ValueError("No active Telegram session found.")

    if not session.api_id or not session.api_hash:
        raise ValueError("API credentials missing from session.")

    client = await get_or_restore_client(
        session_id=session_id,
        api_id=session.api_id,
        api_hash=session.api_hash,
        session_string=session.session_string,
    )
    return client
