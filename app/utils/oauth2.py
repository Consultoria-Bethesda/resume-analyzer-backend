from authlib.integrations.starlette_client import OAuth
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)

# Criar instância do OAuth
oauth = OAuth()

# Registrar o cliente Google OAuth2
try:
    oauth.register(
        name='google',
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )
    logger.info("Google OAuth configurado com sucesso")
except Exception as e:
    logger.error(f"Erro ao configurar Google OAuth: {str(e)}")

# Exportar a instância oauth
__all__ = ['oauth']