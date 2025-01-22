import os
import sys
from dotenv import load_dotenv

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Carrega as variáveis de ambiente do arquivo test.env
load_dotenv('test.env')

from sqlalchemy import create_engine
from app.database import Base
from app.models.user import User
from app.models.user_credits import UserCredits

def create_tables():
    try:
        database_url = "postgresql://postgres:postgres@localhost:5432/resume_analyzer_test"
        engine = create_engine(database_url)
        
        # Isso criará todas as tabelas definidas nos modelos
        Base.metadata.create_all(bind=engine)
        print("Tabelas criadas com sucesso!")
        
        # Verifica as tabelas criadas
        from sqlalchemy import inspect
        inspector = inspect(engine)
        print("\nTabelas encontradas:")
        for table_name in inspector.get_table_names():
            print(f"- {table_name}")
            
    except Exception as e:
        print(f"Erro: {str(e)}")

if __name__ == "__main__":
    create_tables()
