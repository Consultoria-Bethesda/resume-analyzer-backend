import os
import sys
import shutil
from alembic import command
from alembic.config import Config
from app.config.settings import settings

def reset_and_init_migrations():
    try:
        print("Iniciando reset das migrações...")
        
        # Remove diretório de migrações existente
        if os.path.exists('alembic/versions'):
            shutil.rmtree('alembic/versions')
        os.makedirs('alembic/versions', exist_ok=True)
        
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
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    reset_and_init_migrations()