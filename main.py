from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth, cv_analysis, payment
from app.database import engine, Base
from app.config.settings import settings

app = FastAPI()

# Configuração CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir rotas
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(cv_analysis.router, prefix="/cv", tags=["cv"])
app.include_router(payment.router, prefix="/payment", tags=["payment"])

# Adicionar endpoint de health check
@app.get("/health")
async def health_check():
    return {"status": "ok"}