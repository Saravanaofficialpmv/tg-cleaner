"""
Telegram Cleaner — main FastAPI application.
Run with:  uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from app.routes import auth, dashboard, cleanup

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Telegram Cleaner",
    description="Clean your Telegram groups and channels with ease.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Session Auto-Healing Middleware for Serverless ──────────────────────────
@app.middleware("http")
async def session_restoration_middleware(request: Request, call_next):
    # Try retrieving from headers
    session_id = request.headers.get("x-tg-session-id")
    session_string = request.headers.get("x-tg-session-string")
    api_id_str = request.headers.get("x-tg-api-id")
    api_hash = request.headers.get("x-tg-api-hash")
    phone = request.headers.get("x-tg-phone")

    # Fallback: Try retrieving from query parameters (for SSE and exports)
    if not session_id:
        session_id = request.query_params.get("session_id")
    if not session_string:
        session_string = request.query_params.get("session_string")
    if not api_id_str:
        api_id_str = request.query_params.get("api_id")
    if not api_hash:
        api_hash = request.query_params.get("api_hash")
    if not phone:
        phone = request.query_params.get("phone")

    if session_id and session_string and api_id_str and api_hash and phone:
        try:
            api_id = int(api_id_str)
            # Check if this session is in the DB
            from app.database import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                from app.services import session as sess_service
                from app.models.models import UserSession
                
                session = await sess_service.get_user_session(db, session_id)
                if not session:
                    # Session missing in this Vercel serverless container! Recreate it.
                    new_session = UserSession(
                        session_id=session_id,
                        phone=phone,
                        session_string=session_string,
                        api_id=api_id,
                        api_hash=api_hash,
                        is_active=True,
                    )
                    db.add(new_session)
                    await db.commit()
                    logger.info(f"Dynamically restored session {session_id} in Vercel container.")
        except Exception as e:
            logger.error(f"Failed to auto-heal session in middleware: {e}")
            
    return await call_next(request)

# ── Static files & templates ──────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(cleanup.router, prefix="/api")


# ── Pages ─────────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/cleanup", response_class=HTMLResponse)
async def cleanup_page(request: Request):
    return templates.TemplateResponse("cleanup.html", {"request": request})


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
