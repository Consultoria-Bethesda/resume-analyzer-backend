import os
import sys
from sqlalchemy import create_engine, text, inspect

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.settings import settings

def clean_alembic():
    database_url = f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    engine = create_engine(database_url)
    
    with engine.connect() as connection:
        # Desabilita temporariamente as verificações de chave estrangeira
        connection.execute(text("SET session_replication_role = 'replica';"))
        
        # Lista todas as tabelas existentes
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        print(f"Tabelas encontradas: {tables}")
        
        # Drop todas as tabelas existentes
        for table in tables:
            print(f"Dropping table: {table}")
            connection.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE;"))
        
        # Reabilita as verificações de chave estrangeira
        connection.execute(text("SET session_replication_role = 'origin';"))
        
        connection.commit()

if __name__ == "__main__":
    clean_alembic()
    print("Database cleaned successfully!")
