from fastapi import FastAPI, HTTPException
from app.middleware.security import SecurityMiddleware
from app.routes import auth, cv_analysis, user, payment
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.config.settings import settings
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI(
    title="Resume Analyzer API",
    description="API para análise de currículos",
    version="1.0.0"
)

# Healthcheck endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    }

# Registrar rotas
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(cv_analysis.router, prefix="/cv", tags=["CV Analysis"])
app.include_router(user.router, prefix="/users", tags=["Users"])
app.include_router(payment.router, prefix="/payments", tags=["Payments"])

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

# Tratamento de erros global
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    if isinstance(exc, HTTPException):
        return {"detail": exc.detail}
    return {"detail": "Internal Server Error"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(settings.PORT))

