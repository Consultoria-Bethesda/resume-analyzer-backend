import os
import sys
from sqlalchemy import create_engine, text

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.settings import settings

def clean_database():
    database_url = f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    engine = create_engine(database_url)
    
    with engine.connect() as connection:
        # Desabilita temporariamente as verificações de chave estrangeira
        connection.execute(text("SET session_replication_role = 'replica';"))
        
        # Drop todas as tabelas
        connection.execute(text("DROP TABLE IF EXISTS users CASCADE;"))
        connection.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE;"))
        
        # Reabilita as verificações de chave estrangeira
        connection.execute(text("SET session_replication_role = 'origin';"))
        
        connection.commit()
        print("Banco de dados limpo com sucesso!")

if __name__ == "__main__":
    clean_database()
