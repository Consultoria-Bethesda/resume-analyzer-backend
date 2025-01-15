from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.utils.auth import create_access_token
from app.services.auth import authenticate_user
import requests
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/google/login")
async def login_google():
    return {"url": f"https://accounts.google.com/o/oauth2/v2/auth?response_type=code&client_id={settings.GOOGLE_CLIENT_ID}&redirect_uri={settings.BASE_URL}/auth/google/callback&scope=openid%20email%20profile"}

@router.get("/google/callback")
async def google_callback(code: str, db: Session = Depends(get_db)):
    try:
        logger.info("Recebido callback do Google com código")
        
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": f"{settings.BASE_URL}/auth/google/callback",
            "grant_type": "authorization_code"
        }
        
        response = requests.post(token_url, data=data)
        access_token = response.json().get("access_token")
        
        if not access_token:
            logger.error("Não foi possível obter o token do Google")
            raise HTTPException(status_code=400, detail="Falha na autenticação com Google")
        
        user_info = requests.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        ).json()

        logger.info(f"Informações do usuário obtidas: {user_info.get('email')}")

        user = db.query(User).filter(User.email == user_info["email"]).first()
        if not user:
            logger.info("Criando novo usuário")
            user = User(
                email=user_info["email"],
                name=user_info.get("name"),
                google_id=user_info["id"]
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        jwt_token = create_access_token(data={"sub": user.email})
        logger.info("Token JWT criado")
        
        # Redirecionar para o frontend com o token
        redirect_url = f"{settings.FRONTEND_URL}?token={jwt_token}"
        logger.info(f"Redirecionando para: {redirect_url}")
        
        return RedirectResponse(url=redirect_url)
    
    except Exception as e:
        logger.error(f"Erro no callback: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/register")
async def register(email: str, password: str, name: str, db: Session = Depends(get_db)):
    try:
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email já cadastrado")
        
        user = User(email=email, name=name)
        user.set_password(password)
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        access_token = create_access_token(data={"sub": user.email})
        return {"access_token": access_token, "token_type": "bearer"}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login")
async def login(email: str, password: str, db: Session = Depends(get_db)):
    user = authenticate_user(db, email, password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}