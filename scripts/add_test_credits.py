import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv('test.env')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.user import User
from app.models.user_credits import UserCredits

def add_test_credits():
    try:
        # Criar conexão com o banco
        database_url = "postgresql://postgres:postgres@localhost:5432/resume_analyzer_test"
        engine = create_engine(database_url)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()

        # Criar usuário de teste se não existir
        test_email = "test@example.com"
        user = db.query(User).filter(User.email == test_email).first()
        if not user:
            user = User(email=test_email, is_active=True)
            db.add(user)
            db.commit()
            print(f"Usuário de teste criado: {test_email}")

        # Adicionar ou atualizar créditos
        credits = db.query(UserCredits).filter(UserCredits.user_id == user.id).first()
        if not credits:
            credits = UserCredits(user_id=user.id, remaining_analyses=4)
            db.add(credits)
        else:
            credits.remaining_analyses += 4
        
        db.commit()
        print(f"Créditos adicionados para {test_email}")

    except Exception as e:
        print(f"Erro ao adicionar créditos: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    add_test_credits()
