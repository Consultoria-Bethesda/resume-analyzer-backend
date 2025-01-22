from fastapi import Request, HTTPException
import re
from typing import Pattern
import logging

logger = logging.getLogger(__name__)

class SecurityMiddleware:
    def __init__(self):
        # Padrão estrito para boundary do multipart/form-data
        self.boundary_pattern: Pattern = re.compile(r'^[a-zA-Z0-9\'()+_,-./:=? ]{1,70}$')
        self.max_content_type_length = 256
        
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
                # Validação rápida do formato básico
                if 'boundary=' not in content_type:
                    raise HTTPException(
                        status_code=400,
                        detail="Missing boundary in multipart/form-data"
                    )
                
                # Extração segura do boundary
                parts = content_type.split('boundary=', 1)
                if len(parts) != 2:
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid boundary format"
                    )
                
                boundary = parts[1].split(';')[0].strip()
                
                # Validação do boundary
                if not self.boundary_pattern.match(boundary):
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid boundary characters or length"
                    )
                    
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Multipart validation error: {str(e)}")
                raise HTTPException(status_code=400, detail="Invalid multipart format")

    async def __call__(self, request: Request, call_next):
        await self.validate_multipart(request)
        return await call_next(request)
