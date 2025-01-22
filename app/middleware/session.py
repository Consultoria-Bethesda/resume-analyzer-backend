from fastapi import Request, HTTPException
import re
from typing import Pattern
import logging
from starlette.middleware.sessions import SessionMiddleware as StarletteSessionMiddleware
from app.config.settings import settings

logger = logging.getLogger(__name__)

class SessionMiddleware(StarletteSessionMiddleware):
    def __init__(self, app=None):
        super().__init__(
            app=app,
            secret_key=settings.SECRET_KEY,
            session_cookie="resume_analyzer_session",
            max_age=14 * 24 * 60 * 60,  # 14 dias em segundos
            same_site="lax",
            https_only=settings.ENVIRONMENT == "production"
        )
        logger.info("SessionMiddleware initialized")
