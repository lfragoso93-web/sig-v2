from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import Base, engine
from app.routers import auth, portfolios, transactions, dividends

# Cria tabelas (em produ\u00e7\u00e3o usar Alembic)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SIG v2 API",
    description="Sistema de Investimentos Gerenciado",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,         prefix="/api/v1")
app.include_router(portfolios.router,   prefix="/api/v1")
app.include_router(transactions.router, prefix="/api/v1")
app.include_router(dividends.router,    prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0.0"}
