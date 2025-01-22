from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth_router, payment_router, analysis_router
from app.config.settings import settings
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Configurar CORS
origins = [
    settings.FRONTEND_URL,
    "http://localhost:3000",
    "https://cvsemfrescura.com.br",
    "https://www.cvsemfrescura.com.br"
]

logger.info(f"Configurando CORS com origins: {origins}")
logger.info(f"FRONTEND_URL configurado como: {settings.FRONTEND_URL}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir rotas
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(payment_router, prefix="/payment", tags=["payment"])
app.include_router(analysis_router, prefix="/analysis", tags=["analysis"])

@app.get("/")
async def root():
    return {"message": "API CV Sem Frescura"}

@app.get("/health")
async def health_check():
    logger.info("Health check endpoint acessado")
    return {"status": "healthy", "cors_origins": origins}

