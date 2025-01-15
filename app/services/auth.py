from sqlalchemy.orm import Session
from app.models.user import User
from app.utils.auth import verify_password
import logging

logger = logging.getLogger(__name__)

def authenticate_user(db: Session, email: str, password: str):
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            logger.info(f"Usuário não encontrado: {email}")
            return False
        if not verify_password(password, user.hashed_password):
            logger.info(f"Senha incorreta para usuário: {email}")
            return False
        logger.info(f"Usuário autenticado com sucesso: {email}")
        return user
    except Exception as e:
        logger.error(f"Erro ao autenticar usuário: {str(e)}")
        return False