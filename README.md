# SIG v2 — Sistema de Investimentos Gerenciado

Aplicacao full-stack containerizada para gestao de carteiras de investimentos.

## Stack

| Camada | Tecnologia |
|---|---|
| Frontend | React 18 + Vite + TypeScript |
| Backend | FastAPI (Python 3.12) |
| Banco | PostgreSQL 16 |
| Cache | Redis 7 |
| Cotacoes nacionais | BRAPI |
| Cotacoes internacionais | yfinance (Yahoo Finance) |
| Infra | Docker Compose |

## Inicio rapido

```bash
# 1. Clone e configure variaveis
git clone https://github.com/lfragoso93-web/sig-v2
cd sig-v2
cp .env.example .env
# Edite .env com sua senha e BRAPI_TOKEN

# 2. Suba tudo
docker compose up -d --build

# 3. Acesse
# Frontend:  http://localhost
# API docs:  http://localhost/api/v1/docs
```

## Desenvolvimento local

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev   # http://localhost:5173
```

## Variaveis de ambiente (.env)

| Variavel | Descricao | Obrigatoria |
|---|---|---|
| `POSTGRES_PASSWORD` | Senha do banco | Sim |
| `SECRET_KEY` | Chave JWT | Sim |
| `BRAPI_TOKEN` | Token BRAPI para cotacoes nacionais | Nao (limite menor) |
| `APP_PORT` | Porta de acesso (padrao: 80) | Nao |

## Tipos de ativo suportados

| Tipo | API de cotacao |
|---|---|
| Acao Nacional, FII, ETF Nacional, Tesouro Direto | BRAPI |
| Stock, ETF Internacional | Yahoo Finance (yfinance) |
| Criptomoeda | Yahoo Finance (ticker-USD) |
| Renda Fixa | Manual (sem cotacao automatica) |

## Arquitetura

```
browser -> nginx (frontend) -> /api/* -> FastAPI (backend) -> PostgreSQL
                                                           -> Redis
                                                           -> BRAPI
                                                           -> Yahoo Finance
```

## Scheduler de cotacoes

Cotacoes sao atualizadas automaticamente:
- **Seg-Sex, 9h-18h, a cada 15 minutos** (horario de Brasilia)
- Atualizacao on-demand via `?refresh=true` nos endpoints de posicoes
