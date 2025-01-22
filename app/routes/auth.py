from fastapi import APIRouter, Depends, HTTPException, Response, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.utils.auth import create_access_token
from app.services.auth import authenticate_user
from app.config.settings import settings
from pydantic import BaseModel
import requests
import logging
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)
router = APIRouter()  # Adicionando a definição do router

class UserCreate(BaseModel):
    email: str
    password: str
    name: Optional[str] = None

class LoginData(BaseModel):
    email: str
    password: str

@router.get("/google/login", response_class=JSONResponse)
async def login_google() -> Dict[str, Any]:
    try:
        logger.info("Iniciando processo de login com Google")
        
        # Verificar configurações
        if not settings.GOOGLE_CLIENT_ID:
            logger.error("GOOGLE_CLIENT_ID não configurado")
            return JSONResponse(
                status_code=500,
                content={"detail": "Configuração do Google OAuth não encontrada"}
            )

        auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
        redirect_uri = f"{settings.BASE_URL}/auth/google/callback"
        
        # Log das configurações
        logger.info(f"BASE_URL: {settings.BASE_URL}")
        logger.info(f"Redirect URI: {redirect_uri}")
        
        params = {
            "response_type": "code",
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "consent"
        }
        
        # Construir URL
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        full_url = f"{auth_url}?{query_string}"
        
        logger.info(f"URL do Google gerada: {full_url[:50]}...")
        
        return JSONResponse(
            status_code=200,
            content={"url": full_url},
            headers={
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": settings.FRONTEND_URL,
                "Access-Control-Allow-Credentials": "true"
            }
        )
        
    except Exception as e:
        logger.error(f"Erro ao gerar URL do Google: {str(e)}")
        logger.error(f"Stacktrace: {traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"detail": str(e)},
            headers={"Content-Type": "application/json"}
        )

@router.get("/google/callback")
async def google_callback(code: str, db: Session = Depends(get_db)):
    try:
        logger.info("=== Iniciando callback do Google ===")
        
        # 1. Trocar código por token
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": f"{settings.BASE_URL}/auth/google/callback",
            "grant_type": "authorization_code"
        }
        
        token_response = requests.post(token_url, data=token_data)
        
        if not token_response.ok:
            logger.error(f"Erro ao obter token: {token_response.text}")
            return RedirectResponse(
                url=f"{settings.FRONTEND_URL}/login?error=google_auth_failed",
                status_code=302
            )
        
        token_json = token_response.json()
        access_token = token_json.get("access_token")
        
        if not access_token:
            logger.error("Access token não encontrado na resposta")
            return RedirectResponse(
                url=f"{settings.FRONTEND_URL}/login?error=no_access_token",
                status_code=302
            )
        
        # 2. Obter informações do usuário
        user_info_response = requests.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if not user_info_response.ok:
            logger.error(f"Erro ao obter informações do usuário: {user_info_response.text}")
            return RedirectResponse(
                url=f"{settings.FRONTEND_URL}/login?error=user_info_failed",
                status_code=302
            )
        
        user_info = user_info_response.json()
        
        # 3. Criar ou atualizar usuário
        user = db.query(User).filter(User.email == user_info["email"]).first()
        if not user:
            user = User(
                email=user_info["email"],
                name=user_info.get("name"),
                google_id=user_info["id"],
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        
        # 4. Gerar JWT
        jwt_token = create_access_token(data={"sub": user.email})
        
        # 5. Redirecionar para frontend
        redirect_url = f"{settings.FRONTEND_URL}?token={jwt_token}"
        response = RedirectResponse(url=redirect_url, status_code=302)
        
        # 6. Configurar cookie
        response.set_cookie(
            key="session",
            value=jwt_token,
            httponly=True,
            max_age=None,
            secure=settings.ENVIRONMENT == "production",
            samesite="lax"
        )
        
        logger.info("=== Callback do Google concluído com sucesso ===")
        return response
        
    except Exception as e:
        logger.error(f"Erro no callback do Google: {str(e)}")
        logger.exception("Stacktrace completo:")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/register")
async def register(
    user_data: UserCreate, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    try:
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email já cadastrado")
        
        # Criar usuário como inativo
        user = User(
            email=user_data.email,
            name=user_data.name,
            is_active=False  # Começa inativo
        )
        user.set_password(user_data.password)
        
        # Gerar token de verificação
        verification_token = secrets.token_urlsafe(32)
        user.email_verification_token = verification_token
        user.email_verification_expires = datetime.utcnow() + timedelta(hours=24)
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Enviar email de verificação em background
        background_tasks.add_task(
            send_verification_email,
            user.email,
            verification_token
        )
        
        return {
            "message": "Cadastro realizado com sucesso. Por favor, verifique seu email para ativar sua conta."
        }
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login")
async def login(login_data: LoginData, db: Session = Depends(get_db)):
    user, status = authenticate_user(db, login_data.email, login_data.password)
    
    if status == "NOT_FOUND":
        raise HTTPException(
            status_code=401,
            detail="Usuário não cadastrado. Por favor, registre-se primeiro.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    elif status == "INVALID_PASSWORD":
        raise HTTPException(
            status_code=401,
            detail="Senha incorreta",
            headers={"WWW-Authenticate": "Bearer"},
        )
    elif status == "DB_CONNECTION_ERROR":
        raise HTTPException(
            status_code=503,
            detail="Erro de conexão com o banco de dados. Por favor, tente novamente em alguns instantes.",
        )
    elif status == "DB_ERROR":
        raise HTTPException(
            status_code=500,
            detail="Erro ao acessar o banco de dados. Por favor, tente novamente.",
        )
    elif status == "ERROR":
        raise HTTPException(
            status_code=500,
            detail="Erro interno do servidor",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=401,
            detail="Por favor, verifique seu email para ativar sua conta",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

# Novos modelos Pydantic
class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

# Novas rotas
@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        # Retornamos 200 mesmo se o email não existir para evitar enumeração de usuários
        return JSONResponse(
            status_code=200,
            content={"message": "Se o email existir, você receberá instruções para redefinir sua senha"}
        )
    
    # Gerar token de reset
    reset_token = secrets.token_urlsafe(32)
    user.reset_password_token = reset_token
    user.reset_password_expires = datetime.utcnow() + timedelta(hours=1)
    
    db.commit()
    
    # Enviar email em background
    background_tasks.add_task(
        send_reset_password_email,
        user.email,
        reset_token
    )
    
    return {"message": "Se o email existir, você receberá instruções para redefinir sua senha"}

@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        User.reset_password_token == request.token,
        User.reset_password_expires > datetime.utcnow()
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=400,
            detail="Token inválido ou expirado"
        )
    
    user.set_password(request.new_password)
    user.reset_password_token = None
    user.reset_password_expires = None
    
    db.commit()
    
    return {"message": "Senha alterada com sucesso"}

@router.get("/verify-email/{token}")
async def verify_email(token: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        User.email_verification_token == token,
        User.email_verification_expires > datetime.utcnow()
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=400,
            detail="Token inválido ou expirado"
        )
    
    user.is_active = True
    user.email_verification_token = None
    user.email_verification_expires = None
    
    db.commit()
    
    # Criar token de acesso após verificação
    access_token = create_access_token(data={"sub": user.email})
    return {
        "message": "Email verificado com sucesso",
        "access_token": access_token,
        "token_type": "bearer"
    }

# Função auxiliar para enviar email
async def send_reset_password_email(email: str, token: str):
    try:
        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        
        msg = MIMEMultipart()
        msg['From'] = settings.SMTP_USER
        msg['To'] = email
        msg['Subject'] = "Recuperação de Senha - CV Sem Frescura"
        
        body = f"""
        Olá,
        
        Você solicitou a recuperação de senha. Clique no link abaixo para redefinir sua senha:
        
        {reset_link}
        
        Este link é válido por 1 hora.
        
        Se você não solicitou esta alteração, ignore este email.
        
        Atenciosamente,
        Equipe CV Sem Frescura
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
    except Exception as e:
        logger.error(f"Erro ao enviar email: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Erro ao enviar email de recuperação"
        )

async def send_verification_email(email: str, token: str):
    try:
        verification_link = f"{settings.FRONTEND_URL}/verify-email?token={token}"
        
        msg = MIMEMultipart()
        msg['From'] = settings.SMTP_USER
        msg['To'] = email
        msg['Subject'] = "Verificação de Email - CV Sem Frescura"
        
        body = f"""
        Olá,
        
        Obrigado por se cadastrar no CV Sem Frescura!
        
        Para ativar sua conta, clique no link abaixo:
        
        {verification_link}
        
        Este link é válido por 24 horas.
        
        Se você não se cadastrou em nosso site, ignore este email.
        
        Atenciosamente,
        Equipe CV Sem Frescura
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
    except Exception as e:
        logger.error(f"Erro ao enviar email de verificação: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Erro ao enviar email de verificação"
        )
