import os
import sys
# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from app.database import Base
from app.config.settings import settings
import logging

# Importa todos os modelos para garantir que sejam registrados
from app.models import user, user_credits

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db():
    try:
        database_url = f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
        engine = create_engine(database_url)
        
        # Cria todas as tabelas
        Base.metadata.create_all(bind=engine)
        
        # Verifica as tabelas criadas
        from sqlalchemy import inspect
        inspector = inspect(engine)
        logger.info("Tabelas criadas:")
        for table_name in inspector.get_table_names():
            logger.info(f"- {table_name}")
        
        logger.info("Banco de dados inicializado com sucesso!")
        
    except Exception as e:
        logger.error(f"Erro ao inicializar banco de dados: {str(e)}")
        raise

if __name__ == "__main__":
    init_db()
