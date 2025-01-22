from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from app.models.user import User
from app.utils.auth import verify_password
import logging

logger = logging.getLogger(__name__)

def authenticate_user(db: Session, email: str, password: str):
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            logger.info(f"Usuário não encontrado: {email}")
            return None, "NOT_FOUND"
        if not verify_password(password, user.hashed_password):
            logger.info(f"Senha incorreta para usuário: {email}")
            return None, "INVALID_PASSWORD"
        logger.info(f"Usuário autenticado com sucesso: {email}")
        return user, "SUCCESS"
    except OperationalError as e:
        logger.error(f"Erro de conexão com o banco de dados: {str(e)}")
        return None, "DB_CONNECTION_ERROR"
    except SQLAlchemyError as e:
        logger.error(f"Erro do SQLAlchemy: {str(e)}")
        return None, "DB_ERROR"
    except Exception as e:
        logger.error(f"Erro inesperado ao autenticar usuário: {str(e)}")
        return None, "ERROR"
