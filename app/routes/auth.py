from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from app.utils.oauth2 import oauth
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get('/google/login')
async def google_login(request: Request):
    try:
        redirect_uri = request.url_for('google_auth_callback')
        return await oauth.google.authorize_redirect(request, redirect_uri)
    except Exception as error:
        logger.error(f"Erro no login do Google: {error}")
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/login?error=Login failed",
            status_code=302
        )

@router.get('/google/callback')
async def google_auth_callback(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
        user = await oauth.google.get('https://www.googleapis.com/oauth2/v3/userinfo', token=token)
        user_info = user.json()
        
        logger.info(f"Login bem-sucedido para: {user_info.get('email')}")
        
        # Gera o token de acesso
        access_token = token['access_token']
        
        # Redireciona para o frontend com o token
        frontend_url = f"{settings.FRONTEND_URL}/?token={access_token}"
        logger.info(f"Redirecionando para: {frontend_url}")
        
        response = RedirectResponse(url=frontend_url)
        response.status_code = 302
        return response

    except Exception as error:
        logger.error(f"Erro no callback do Google: {error}")
        error_redirect = f"{settings.FRONTEND_URL}/login?error=Authentication failed"
        return RedirectResponse(url=error_redirect, status_code=302)