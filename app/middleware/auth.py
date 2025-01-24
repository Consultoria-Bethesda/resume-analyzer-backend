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
    logger.info("Iniciando validação de token")
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        if not token:
            logger.error("Token não fornecido")
            raise credentials_exception
            
        # Remover prefixo "Bearer " se presente
        if token.startswith('Bearer '):
            token = token.split(' ')[1]
            
        logger.info(f"Token recebido (primeiros 20 caracteres): {token[:20]}...")
        email = decode_token(token)
        
        if email is None:
            logger.error("Email não encontrado no token")
            raise credentials_exception
            
        user = db.query(User).filter(User.email == email).first()
        logger.info(f"Usuário encontrado: {user.email if user else 'Nenhum'}")
        
        if user is None:
            logger.error("Usuário não encontrado no banco de dados")
            raise credentials_exception
            
        return user
        
    except Exception as e:
        logger.error(f"Erro durante validação do token: {str(e)}")
        raise credentials_exception
