from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from sqlalchemy.orm import Session
from app.database import SessionLocal
from starlette.middleware.sessions import SessionMiddleware as StarletteSessionMiddleware
from app.config.settings import settings

class SessionMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.session_middleware = StarletteSessionMiddleware(
            app,
            secret_key=settings.SECRET_KEY,
            session_cookie="session",
            max_age=None,  # Cookie expira quando o navegador fecha
            same_site="lax",
            https_only=True if settings.ENVIRONMENT == "production" else False
        )

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Força o fechamento da sessão após cada requisição
        if hasattr(request.state, "db"):
            request.state.db.close()
            request.state.db.remove()
        
        return response
