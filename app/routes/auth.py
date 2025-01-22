from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import JSONResponse
from app.config.settings import settings
import logging
from urllib.parse import urlencode

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/google/login")
async def login_google():
    try:
        logger.info("Iniciando processo de login com Google")
        logger.info(f"GOOGLE_CLIENT_ID configurado: {bool(settings.GOOGLE_CLIENT_ID)}")
        logger.info(f"FRONTEND_URL: {settings.FRONTEND_URL}")
        
        if not settings.GOOGLE_CLIENT_ID:
            logger.error("GOOGLE_CLIENT_ID não configurado")
            raise HTTPException(
                status_code=500,
                detail="Configuração do Google OAuth não encontrada"
            )

        # Construir URL do Google OAuth
        auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
        redirect_uri = f"{settings.FRONTEND_URL}/auth/google/callback"
        
        params = {
            "response_type": "code",
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "consent"
        }
        
        # Construir URL completa
        full_url = f"{auth_url}?{urlencode(params)}"
        
        logger.info(f"URL do Google gerada: {full_url[:50]}...")
        
        return JSONResponse(
            content={"url": full_url},
            headers={
                "Access-Control-Allow-Origin": settings.FRONTEND_URL,
                "Access-Control-Allow-Credentials": "true",
            }
        )
        
    except Exception as e:
        logger.error(f"Erro ao gerar URL do Google: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
