from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import settings

app = FastAPI()

# Configuração do CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir rotas
from app.routes.auth import router as auth_router
from app.routes.cv_analysis import router as cv_analysis_router
from app.routes.user import router as user_router
from app.routes.payment import router as payment_router

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(cv_analysis_router, prefix="/cv", tags=["cv"])
app.include_router(user_router, prefix="/user", tags=["user"])
app.include_router(payment_router, prefix="/payment", tags=["payment"])

@app.get("/")
async def root():
    return {"message": "API CV Sem Frescura"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "frontend_url": settings.FRONTEND_URL,
        "backend_url": settings.BACKEND_URL
    }

