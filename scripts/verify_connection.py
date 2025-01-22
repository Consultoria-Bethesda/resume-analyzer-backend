import os
import sys
from dotenv import load_dotenv

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Carrega as variáveis de ambiente do arquivo test.env
load_dotenv('test.env')

def verify_connection():
    try:
        # Usa a DATABASE_URL diretamente do test.env
        database_url = os.getenv('DATABASE_URL')
        print(f"Tentando conectar a: {database_url}")
        
        from sqlalchemy import create_engine, inspect
        engine = create_engine(database_url)
        inspector = inspect(engine)
        
        print("\nTabelas encontradas:")
        for table_name in inspector.get_table_names():
            print(f"- {table_name}")
            
        with engine.connect() as conn:
            print("\nConexão estabelecida com sucesso!")
            
    except Exception as e:
        print(f"Erro: {str(e)}")

if __name__ == "__main__":
    verify_connection()
