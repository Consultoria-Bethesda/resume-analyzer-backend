from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth_router, payment_router, analysis_router

app = FastAPI()

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://cvsemfrescura.com.br",
        "http://localhost:3000"  # para desenvolvimento local
    ],
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
    return {"status": "healthy"}

