from fastapi import Request, HTTPException
import re
from typing import Pattern
import logging

logger = logging.getLogger(__name__)

class SecurityMiddleware:
    def __init__(self, app):
        self.app = app
        # Padrão estrito para boundary do multipart/form-data
        self.boundary_pattern: Pattern = re.compile(r'^[a-zA-Z0-9\'()+_,-./:=? ]{1,70}$')
        self.max_content_type_length = 256
        
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        request = Request(scope, receive)
        try:
            # Validação do Content-Type para requisições multipart
            await self.validate_multipart(request)
            return await self.app(scope, receive, send)
            
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Erro no SecurityMiddleware: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Internal server error during security checks"
            )

    async def validate_multipart(self, request: Request) -> None:
        content_type = request.headers.get('content-type', '')
        
        if not content_type:
            return
            
        # Proteção contra ReDoS no Content-Type
        if len(content_type) > self.max_content_type_length:
            raise HTTPException(
                status_code=400, 
                detail="Content-Type header too long"
            )
            
        # Validação específica para multipart/form-data
        if content_type.startswith('multipart/form-data'):
            try:
                # Extrai e valida o boundary
                boundary = content_type.split('boundary=')[-1].strip()
                if not self.boundary_pattern.match(boundary):
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid multipart boundary"
                    )
            except Exception:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid Content-Type format"
                )
