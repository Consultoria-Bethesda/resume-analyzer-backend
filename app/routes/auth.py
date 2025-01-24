from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import settings
from urllib.parse import urlencode
import requests
from jose import jwt
from datetime import datetime, timedelta
from app.models.user import User
from app.database import get_db
from sqlalchemy.orm import Session
from fastapi import Depends
from app.utils.auth import create_access_token
from app.middleware.auth import get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/google/login")
async def google_login():
    try:
        # Parâmetros para a URL de autorização do Google
        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": f"{settings.BACKEND_URL}/auth/google/callback",
            "response_type": "code",
            "scope": "openid email profile",
            "state": "google_auth",  # Estado para verificação de segurança
            "access_type": "offline",
            "prompt": "consent"
        }
        
        # Construir a URL de autorização do Google
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
        
        # Retornar a URL para o frontend
        return {"url": auth_url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/google/callback")
async def google_callback(request: Request, code: str, state: str, db: Session = Depends(get_db)):
    try:
        logger.info("=== Starting Google Callback ===")
        logger.info(f"Code: {code[:10]}... (truncated)")
        logger.info(f"State: {state}")
        
        if state != "google_auth":
            logger.error("Invalid state parameter")
            raise HTTPException(status_code=400, detail="Invalid state parameter")

        # Log das configurações
        logger.info(f"FRONTEND_URL: {settings.FRONTEND_URL}")
        logger.info(f"BACKEND_URL: {settings.BACKEND_URL}")

        # Troca o código de autorização por tokens
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": f"{settings.BACKEND_URL}/auth/google/callback",
            "grant_type": "authorization_code"
        }

        logger.info("Requesting token from Google with data:")
        logger.info(f"Redirect URI: {token_data['redirect_uri']}")
        
        token_response = requests.post(token_url, data=token_data)
        logger.info(f"Google token response status: {token_response.status_code}")
        
        if not token_response.ok:
            logger.error(f"Failed to get token from Google: {token_response.text}")
            raise HTTPException(status_code=400, detail="Failed to get token from Google")

        token_info = token_response.json()
        logger.info("Successfully received token from Google")

        # Obtém informações do usuário
        userinfo_response = requests.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {token_info['access_token']}"}
        )
        
        if not userinfo_response.ok:
            logger.error(f"Failed to get user info: {userinfo_response.text}")
            raise HTTPException(status_code=400, detail="Failed to get user info from Google")

        user_info = userinfo_response.json()
        logger.info(f"Received user info for email: {user_info.get('email')}")

        # Verifica se o usuário já existe ou cria um novo
        user = db.query(User).filter(User.email == user_info['email']).first()
        if not user:
            logger.info(f"Creating new user for email: {user_info['email']}")
            user = User(
                email=user_info['email'],
                name=user_info.get('name', ''),
                is_active=True,
                auth_provider='google',
                google_id=user_info.get('sub')
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        # Cria o token JWT
        token_data = {"sub": user_info['email']}
        token = create_access_token(token_data)
        logger.info(f"Token JWT criado (primeiros 20 caracteres): {token[:20]}...")

        # Construir URL de redirecionamento
        redirect_url = f"{settings.FRONTEND_URL}/auth/google/callback?token={token}"
        logger.info(f"Final redirect URL: {redirect_url}")
        
        response = RedirectResponse(url=redirect_url, status_code=303)
        return response

    except Exception as e:
        logger.error(f"Error in callback: {str(e)}")
        error_redirect = f"{settings.FRONTEND_URL}/login?error={str(e)}"
        return RedirectResponse(url=error_redirect, status_code=303)

@router.get("/validate-token")
async def validate_token(current_user: User = Depends(get_current_user)):
    """
    Endpoint para validar o token JWT.
    Retorna 200 se o token for válido, 401 se inválido.
    """
    return {"valid": True, "user_email": current_user.email}
