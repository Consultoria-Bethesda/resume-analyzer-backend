import os
import sys
from dotenv import load_dotenv
from alembic import command
from alembic.config import Config

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_migrations():
    try:
        # Carrega variáveis de ambiente
        load_dotenv()
        
        print("Iniciando migrações...")
        
        # Configura o Alembic
        alembic_cfg = Config("alembic.ini")
        
        # Aplica as migrações
        command.upgrade(alembic_cfg, "head")
        
        print("Migrações aplicadas com sucesso!")
        
    except Exception as e:
        print(f"Erro ao aplicar migrações: {str(e)}")
        raise

if __name__ == "__main__":
    run_migrations()