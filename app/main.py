from fastapi import FastAPI
from app.middleware.security import SecurityMiddleware
from app.routes import auth_router, cv_router, user_router, payment_router
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.config.settings import settings
from starlette.middleware.sessions import SessionMiddleware

# Importa todos os modelos para garantir que sejam registrados
from app.models import user, user_credits

app = FastAPI()

# Adiciona o SecurityMiddleware
app.add_middleware(SecurityMiddleware)

# Adiciona o SessionMiddleware
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    session_cookie="resume_analyzer_session",
    max_age=14 * 24 * 60 * 60,  # 14 dias em segundos
    same_site="lax",
    https_only=settings.ENVIRONMENT == "production"
)

# Configuração CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir rotas
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(cv_router, prefix="/cv", tags=["cv"])
app.include_router(user_router, prefix="/user", tags=["user"])
app.include_router(payment_router, prefix="/payment", tags=["payment"])

# Criar todas as tabelas
Base.metadata.create_all(bind=engine)

