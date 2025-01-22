import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.user_credits import UserCredits
from app.models.user import User

def check_credits():
    try:
        # Usar a mesma URL do banco que os outros scripts
        database_url = "postgresql://postgres:postgres@localhost:5432/resume_analyzer_test"
        engine = create_engine(database_url)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()

        # Primeiro, vamos verificar se as tabelas existem
        from sqlalchemy import inspect
        inspector = inspect(engine)
        print("\nTabelas encontradas no banco:")
        for table_name in inspector.get_table_names():
            print(f"- {table_name}")

        # Agora consultar os créditos
        credits = db.query(UserCredits, User).join(User).all()
        
        print("\n=== Créditos dos Usuários ===")
        for credit, user in credits:
            print(f"\nUsuário: {user.email}")
            print(f"ID: {user.id}")
            print(f"Créditos restantes: {credit.remaining_analyses}")
            print("-" * 30)

    except Exception as e:
        print(f"Erro ao consultar créditos: {str(e)}")
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    check_credits()
