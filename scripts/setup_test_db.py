import os
import sys
from sqlalchemy_utils import create_database, database_exists, drop_database
from sqlalchemy import create_engine
from alembic import command
from alembic.config import Config
from dotenv import load_dotenv

def setup_test_db():
    # Define a URL do banco de dados diretamente
    database_url = "postgresql://postgres:postgres@localhost:5432/resume_analyzer_test"
    
    print(f"Configurando banco de dados com URL: {database_url}")
    
    try:
        # Recria o banco de dados
        if database_exists(database_url):
            print("Removendo banco de dados existente...")
            drop_database(database_url)
        
        print("Criando novo banco de dados...")
        create_database(database_url)
        
        print("Aplicando migrações...")
        alembic_cfg = Config("alembic.ini")
        
        # Configura a URL do banco no alembic.ini em tempo de execução
        alembic_cfg.set_main_option("sqlalchemy.url", database_url)
        
        command.upgrade(alembic_cfg, "head")
        
        print("Banco de dados configurado com sucesso!")
        
    except Exception as e:
        print(f"Erro durante a configuração do banco: {str(e)}")
        raise

if __name__ == "__main__":
    # Adiciona o diretório raiz ao PYTHONPATH
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    setup_test_db()

