import os
import sys
import shutil
from alembic import command
from alembic.config import Config

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.settings import settings

def reset_and_init_migrations():
    try:
        print("Iniciando reset das migrações...")
        
        # Remove diretório de migrações existente
        versions_dir = 'alembic/versions'
        if os.path.exists(versions_dir):
            print(f"Removendo diretório: {versions_dir}")
            shutil.rmtree(versions_dir)
        os.makedirs(versions_dir, exist_ok=True)
        
        # Remove a tabela alembic_version se existir
        from sqlalchemy import create_engine, text
        database_url = f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
        engine = create_engine(database_url)
        with engine.connect() as conn:
            conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
            conn.commit()
        
        # Configura Alembic
        alembic_cfg = Config("alembic.ini")
        
        # Cria nova migração inicial
        print("Criando nova migração inicial...")
        command.revision(alembic_cfg, 
                        autogenerate=True,
                        message="initial_migration")
        
        print("Migrações resetadas com sucesso!")
        
    except Exception as e:
        print(f"Erro ao resetar migrações: {str(e)}")
        raise

if __name__ == "__main__":
    reset_and_init_migrations()
