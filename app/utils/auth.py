from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=365)  # 1 ano
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt

def decode_token(token: str):
    try:
        logger.info("Iniciando decodificação do token")
        logger.info(f"Token recebido (primeiros 20 caracteres): {token[:20]}...")
        
        if not token or not isinstance(token, str):
            logger.error(f"Token inválido: {token}")
            return None
        
        # Remover prefixo "Bearer " se presente
        if token.startswith('Bearer '):
            token = token.split(' ')[1]
            
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        logger.info(f"Payload decodificado: {payload}")
        
        email: str = payload.get("sub")
        if email is None:
            logger.error("Email não encontrado no payload do token")
            return None
            
        logger.info(f"Email extraído do token: {email}")
        return email
        
    except jwt.JWSError as e:
        logger.error(f"Erro de assinatura JWT: {str(e)}")
        return None
    except jwt.ExpiredSignatureError as e:
        logger.error(f"Token JWT expirado: {str(e)}")
        return None
    except jwt.JWTError as e:
        logger.error(f"Erro ao decodificar token JWT: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Erro inesperado ao decodificar token: {str(e)}")
        return None

def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str):
    return pwd_context.hash(password)
