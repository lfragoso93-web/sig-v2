# SGI v2 — Sistema de Gestão de Investimentos

> Plataforma pessoal de acompanhamento e análise de investimentos.
> Monorepo com backend FastAPI e frontend React + TypeScript.

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-blue)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-blue)](https://typescriptlang.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)](https://docker.com)

---

## Funcionalidades implementadas

### Dashboard Principal (`/`)
- **4 KpiCards** com dados precisos via `rentabilidade/kpis`: Patrimônio Total, Resultado Total (com breakdown não-realizado/realizado), Proventos 12m e Rentabilidade (mês + 12m + desde início)
- **Evolução patrimonial** — gráfico de barras com filtro de período (6m/12m/24m/todo) e por classe de ativo
- **Distribuição por classe** — gráfico donut
- **Tabela de posições** agrupada por classe com qtd, preço médio, valor atual e variação

### Rentabilidade (`/carteira/rentabilidade`)
- **8 KpiCards** em 2 linhas: patrimônio, retorno total/mês/12m, ganhos realizados/não-realizados, proventos e custo médio
- **Gráfico de rentabilidade mensal** com comparativo de benchmarks:
  - Barras: retorno % mês a mês da carteira
  - IBOV (BRAPI), CDI (BCB série 4391), IPCA (BCB série 433) — toggles independentes
  - Filtro de período: 6m / 12m / 24m / todo período
- **Distribuição por classe** com barras de alocação e retorno colorido
- **Tabela por ativo**: Qtd · P.M. · Val. atual · Ganho não-realizado · Ganho realizado · Total PnL
- Filtro de tipo de ativo e toggle de posições zeradas

### Outras páginas
- **Patrimônio** — evolução diária/mensal, resumo mensal com rentabilidade por linha
- **Transações** — histórico completo com filtros, gráfico de aportes mensais
- **Proventos** — histórico de dividendos e JCP com gráficos
- **IRPF** — apuração de ganho de capital (em construção)
- **Metas** — CRUD com progresso automático (em construção)
- **Renda Fixa** — cadastro e acompanhamento (em construção)

---

## Stack tecnológica

### Backend
| Tecnologia | Versão | Uso |
|---|---|---|
| Python | 3.12 | Linguagem base |
| FastAPI | 0.115 | Framework web async |
| SQLAlchemy | 2.x async | ORM |
| Alembic | 1.x | Migrations |
| PostgreSQL | 15 | Banco de dados |
| Redis | 7 | Cache (TTL configurável por endpoint) |
| APScheduler | 3.x | Jobs agendados (7 jobs) |
| BRAPI | v2 | Cotações, histórico, Tesouro, FX |
| yfinance | — | Fallback ativos internacionais |
| Alpha Vantage | — | Fallback internacional (4 req/min) |
| SlowAPI | — | Rate limiter global |
| bcrypt | v5 | Hash de senhas |
| JWT | — | Auth com refresh token rotativo |

### Frontend
| Tecnologia | Versão | Uso |
|---|---|---|
| React | 18 | UI |
| TypeScript | 5.x | Tipagem |
| Vite | 5.x | Build tool |
| TailwindCSS | 3.x | Utilitários CSS |
| Recharts | 2.x | Gráficos (barras, linha, donut, compostos) |
| React Query | 5.x | Cache e estado servidor |
| Zustand | — | Estado global (carteira selecionada) |
| Lucide React | — | Ícones |
| Axios | — | HTTP client |

---

## Estrutura do projeto

```
sig-v2/
├── backend/
│   ├── app/
│   │   ├── core/          # database, deps, settings, scheduler
│   │   ├── models/        # SQLAlchemy models
│   │   ├── routers/       # endpoints FastAPI
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── services/      # lógica de negócio
│   │   └── integrations/  # BRAPI, yfinance, Alpha Vantage, BCB
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── components/    # UI components, charts, modals
│   │   ├── hooks/         # React Query hooks
│   │   ├── pages/         # páginas da aplicação
│   │   ├── services/      # HTTP services
│   │   ├── store/         # Zustand stores
│   │   └── styles/        # CSS vars + design system
│   └── public/
├── docker-compose.yml
├── docker-compose.prod.yml
├── CHANGELOG.md
├── ROADMAP_SPRINTS.md
└── README.md
```

---

## Como rodar

### Com Docker (recomendado)

```bash
cp .env.example .env
# edite o .env com suas chaves (BRAPI_TOKEN, SECRET_KEY, etc.)
docker compose up --build
```

Acesse:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- Swagger: http://localhost:8000/docs

### Sem Docker

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

---

## Variáveis de ambiente

Copie `.env.example` e preencha:

| Variável | Descrição |
|---|---|
| `DATABASE_URL` | URL PostgreSQL (ex: `postgresql+asyncpg://user:pass@localhost/db`) |
| `REDIS_URL` | URL Redis (ex: `redis://localhost:6379`) |
| `SECRET_KEY` | Chave JWT (mínimo 32 chars) |
| `BRAPI_TOKEN` | Token BRAPI (plano free funciona para cotações básicas) |
| `ALPHA_VANTAGE_KEY` | Chave Alpha Vantage (opcional, fallback internacional) |
| `SUPERADMIN_EMAIL` | E-mail do superadmin criado no boot |
| `SUPERADMIN_PASSWORD` | Senha do superadmin |

---

## Roadmap

Veja o roadmap completo em [ROADMAP_SPRINTS.md](./ROADMAP_SPRINTS.md).

**Próximas prioridades (Sprint 5 — em andamento):**
- Tela de metas financeiras
- Tela IRPF com exportação de relatório
- Tela de renda fixa
- Fix `YFRateLimitError` para ativos internacionais

---

## Changelog

Veja o histórico completo em [CHANGELOG.md](./CHANGELOG.md).
