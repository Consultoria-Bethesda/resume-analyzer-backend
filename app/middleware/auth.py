from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.utils.auth import decode_token
import logging

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    logger.info("Verificando token: " + token)
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        email = decode_token(token)
        logger.info("Email encontrado no token: " + email)
        if email is None:
            raise credentials_exception
    except Exception as e:
        logger.error(f"Erro ao decodificar token: {str(e)}")
        raise credentials_exception
    
    user = db.query(User).filter(User.email == email).first()
    logger.info(f"Usuário encontrado: {user.email if user else 'None'}")
    
    if user is None:
        raise credentials_exception
    return user