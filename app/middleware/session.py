from fastapi import Request, HTTPException
import re
from typing import Pattern
import logging

logger = logging.getLogger(__name__)

class SecurityMiddleware:
    def __init__(self):
        # Padrão seguro para boundary do multipart/form-data
        self.boundary_pattern: Pattern = re.compile(r'^[a-zA-Z0-9\'()+_,-./:=? ]{1,70}$')
        self.max_content_type_length = 256
        
    async def validate_multipart(self, request: Request) -> None:
        content_type = request.headers.get('content-type', '')
        
        # Validação básica do Content-Type
        if not content_type:
            return
            
        # Proteção contra ReDoS no Content-Type
        if len(content_type) > self.max_content_type_length:
            raise HTTPException(
                status_code=400, 
                detail="Content-Type header exceeds maximum length"
            )
            
        # Validação específica para multipart/form-data
        if 'multipart/form-data' in content_type:
            try:
                # Extrai e valida o boundary
                if 'boundary=' not in content_type:
                    raise HTTPException(
                        status_code=400,
                        detail="Missing boundary in multipart/form-data"
                    )
                
                boundary = content_type.split('boundary=')[-1].split(';')[0].strip()
                
                # Valida o boundary contra o padrão seguro
                if not self.boundary_pattern.match(boundary):
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid multipart/form-data boundary format"
                    )
                    
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Multipart validation error: {str(e)}")
                raise HTTPException(
                    status_code=400, 
                    detail="Invalid multipart/form-data format"
                )

    async def __call__(self, request: Request, call_next):
        try:
            await self.validate_multipart(request)
            response = await call_next(request)
            return response
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Security middleware error: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid request format")
