import os
import sys
from alembic import command
from alembic.config import Config

def apply_migrations():
    try:
        # Configura o Alembic
        alembic_cfg = Config("alembic.ini")
        
        # Aplica todas as migrações pendentes
        command.upgrade(alembic_cfg, "head")
        
        print("Migrações aplicadas com sucesso!")
        
    except Exception as e:
        print(f"Erro ao aplicar migrações: {str(e)}")
        raise

if __name__ == "__main__":
    # Adiciona o diretório raiz ao PYTHONPATH
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    apply_migrations()