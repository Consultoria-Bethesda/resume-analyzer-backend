from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, HTTPException
from sqlalchemy.orm import Session
from app.database import SessionLocal
from starlette.middleware.sessions import SessionMiddleware as StarletteSessionMiddleware
from app.config.settings import settings
import re
from typing import Pattern
import logging

logger = logging.getLogger(__name__)

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

class SecurityMiddleware:
    def __init__(self):
        # Padrão seguro para boundary do multipart/form-data
        self.boundary_pattern: Pattern = re.compile(r'^[a-zA-Z0-9\'()+_,-./:=? ]{1,70}$')
        
    async def validate_multipart(self, request: Request) -> None:
        content_type = request.headers.get('content-type', '')
        
        # Validação básica do Content-Type
        if not content_type:
            return
            
        # Proteção contra ReDoS no Content-Type
        if len(content_type) > 256:  # Limite razoável para um header
            raise HTTPException(status_code=400, detail="Content-Type header too long")
            
        # Validação específica para multipart/form-data
        if 'multipart/form-data' in content_type:
            try:
                # Extrai o boundary
                boundary = content_type.split('boundary=')[-1].split(';')[0]
                
                # Valida o boundary
                if not self.boundary_pattern.match(boundary):
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid multipart/form-data boundary"
                    )
                    
                # Verifica o tamanho do boundary
                if len(boundary) > 70:  # RFC 2046 recomenda limite de 70 caracteres
                    raise HTTPException(
                        status_code=400,
                        detail="Boundary length exceeds limit"
                    )
                    
            except Exception as e:
                logger.error(f"Multipart validation error: {str(e)}")
                raise HTTPException(status_code=400, detail="Invalid multipart format")

    async def __call__(self, request: Request, call_next):
        try:
            await self.validate_multipart(request)
            response = await call_next(request)
            return response
        except Exception as e:
            logger.error(f"Security middleware error: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid request format")
