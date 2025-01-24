import os
from dotenv import load_dotenv
from alembic import command
from alembic.config import Config

def run_migrations():
    # Carrega variáveis de ambiente
    load_dotenv()
    
    # Configura o Alembic
    alembic_cfg = Config("alembic.ini")
    
    # Aplica as migrações
    command.upgrade(alembic_cfg, "head")

if __name__ == "__main__":
    run_migrations()
