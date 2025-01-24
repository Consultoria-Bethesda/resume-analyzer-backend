import os
import sys
import logging
from sqlalchemy import create_engine
from app.database import Base
from app.config.settings import settings

# Configuração do logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db():
    try:
        database_url = f"postgresql://{settings.PGUSER}:{settings.PGPASSWORD}@{settings.PGHOST}:{settings.PGPORT}/{settings.PGDATABASE}"
        logger.info(f"Conectando ao banco de dados: {database_url}")
        
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
