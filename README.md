# SGI v2 — Sistema de Gerenciamento de Investimentos

> Plataforma pessoal para gestão de carteira de investimentos com suporte a Ações, FIIs, BDRs, ETFs, Stocks internacionais, Tesouro Direto, Renda Fixa e Criptomoedas.

---

## Stack

| Camada | Tecnologia |
|---|---|
| Backend | FastAPI + SQLAlchemy async + Alembic |
| Banco de dados | PostgreSQL 16 |
| Cache | Redis 7 |
| Frontend | React + TypeScript + Vite |
| Containerização | Docker Compose |
| Dados de mercado | BRAPI v2 + Alpha Vantage + yfinance |

---

## Início Rápido

```bash
# 1. Clone o repositório
git clone https://github.com/lfragoso93-web/sig-v2.git
cd sig-v2

# 2. Configure as variáveis de ambiente
cp .env.example .env
# edite .env com suas chaves de API

# 3. Suba os serviços
docker compose up -d --build

# 4. Acesse
# Frontend:  http://localhost:5173
# API Docs:  http://localhost:8000/docs
# Login:     admin@sgi.com / (definido no .env)
```

---

## Variáveis de Ambiente

Copie `.env.example` e preencha:

| Variável | Descrição |
|---|---|
| `POSTGRES_*` | Credenciais do banco |
| `REDIS_URL` | URL do Redis |
| `SECRET_KEY` | Chave JWT (mín. 32 chars) |
| `BRAPI_TOKEN` | Token da BRAPI (gratuito em brapi.dev) |
| `ALPHA_VANTAGE_KEY` | Chave Alpha Vantage (opcional, para ativos internacionais) |
| `SUPERADMIN_EMAIL` | E-mail do superadmin criado no boot |
| `SUPERADMIN_PASSWORD` | Senha do superadmin |

---

## Arquitetura

```
sig-v2/
├── backend/
│   ├── app/
│   │   ├── core/          # config, database, limiter, scheduler, cache
│   │   ├── models/        # SQLAlchemy models
│   │   ├── routers/       # endpoints FastAPI
│   │   ├── services/      # lógica de negócio
│   │   ├── integrations/  # BRAPI, Alpha Vantage
│   │   └── main.py        # app FastAPI + lifespan
│   ├── alembic/           # migrations
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/    # UI components (modais, dashboard, etc.)
│   │   ├── hooks/         # React Query hooks
│   │   ├── pages/         # páginas da aplicação
│   │   ├── store/         # Zustand store
│   │   └── services/      # chamadas à API
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
├── CHANGELOG.md
└── ROADMAP_SPRINTS.md
```

---

## Classes de Ativos Suportadas

| Classe | Moeda | Fonte de Dados |
|---|---|---|
| Ação (ACAO) | BRL | BRAPI v2 |
| FII | BRL | BRAPI v2 |
| ETF Nacional | BRL | BRAPI v2 |
| BDR | BRL | BRAPI v2 |
| Stock Internacional | USD | Alpha Vantage + yfinance |
| ETF Internacional | USD | Alpha Vantage + yfinance |
| Tesouro Direto | BRL | BRAPI v2 |
| Renda Fixa | BRL | Manual |
| Criptomoeda | BRL | BRAPI v2 |

---

## Sequência de Boot

Ao subir o container, o backend executa automaticamente:

1. **Migrations** — Alembic aplica todas as migrations pendentes
2. **Superadmin** — Cria ou atualiza o usuário admin
3. **API disponível** — Uvicorn já aceita requests
4. **[Background] Etapa 1** — Seed de tickers via BRAPI (só se `assets` estiver vazia)
5. **[Background] Etapa 2** — Backfill de 10 anos de preços por ordem: ACAO → FII → ETF → STOCK → BDR

> Proventos são calculados automaticamente a cada nova transação inserida.

---

## Módulos da API

| Prefixo | Descrição |
|---|---|
| `/api/v1/auth` | Login, refresh token, logout |
| `/api/v1/users` | CRUD de usuários |
| `/api/v1/admin` | Operações de superadmin (seed de ativos, etc.) |
| `/api/v1/portfolios` | Carteiras, transações, proventos, Tesouro |
| `/api/v1/positions` | Posições consolidadas por carteira |
| `/api/v1/performance` | Rentabilidade e TWR |
| `/api/v1/assets` | Catálogo de ativos |
| `/api/v1/quotes` | Cotações em tempo real |
| `/api/v1/prices` | Histórico de preços OHLCV |
| `/api/v1/fx` | Câmbio (pares BRL/USD/EUR) |
| `/api/v1/goals` | Metas financeiras |
| `/api/v1/irpf` | Cálculo de IR sobre ganho de capital |
| `/api/v1/analysis` | Score de diversificação e análise |
| `/api/v1/fixed-income` | Renda fixa (CDB, LCI, LCA, Debêntures) |
| `/api/v1/sync` | Sincronização manual de dados |

---

## Status

> **Sprint 4 concluída** — Catálogo de ativos com 2.259 tickers B3, backfill histórico de 10 anos, modal de transações com todas as classes (incluindo BDR).
>
> Próximo: Sprint 5 — Dashboard frontend completo.

Consulte [ROADMAP_SPRINTS.md](./ROADMAP_SPRINTS.md) para o planejamento detalhado e [CHANGELOG.md](./CHANGELOG.md) para o histórico de mudanças.
