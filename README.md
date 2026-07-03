# SGI v2 — Sistema de Gestão de Investimentos

> Plataforma pessoal de acompanhamento e análise de investimentos.
> Monorepo com backend FastAPI e frontend React + TypeScript.

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.138-green)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-blue)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-6.x-blue)](https://typescriptlang.org)
[![Vite](https://img.shields.io/badge/Vite-8.1-purple)](https://vitejs.dev)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)](https://docker.com)

---

## Funcionalidades implementadas

### Dashboard Principal (`/`)
- **4 KpiCards** com dados via `rentabilidade/kpis`: Patrimônio Total, Resultado Total, Proventos 12m e Rentabilidade
- **Evolução patrimonial** com filtro de período (6m/12m/24m/todo) e por classe de ativo
- **Fallback automático** quando não existem snapshots: o backend calcula a série on-the-fly e dispara backfill em background
- **Distribuição por classe** com gráfico donut
- **Tabela de posições** agrupada por classe com qtd, preço médio, valor atual e variação

### Rentabilidade (`/carteira/rentabilidade`)
- **8 KpiCards** em 2 linhas com visão consolidada da carteira
- **Gráfico de rentabilidade mensal** com benchmarks IBOV, CDI e IPCA
- **Distribuição por classe** com barras de alocação e retorno
- **Tabela por ativo** com filtros e toggle de posições zeradas
- **Renda Fixa** calculada corretamente: rendimento por investimento com `asset_type` normalizado e sessão isolada

### Patrimônio (`/carteira/patrimonio`) — Sprint 6B
- **Aba Visão Geral**: KPIs + evolução mensal em barras + gráfico donut de alocação por classe + Distribuição Ideal vs. Atual + tabela de posições
- **Aba Análise**: Score de concentração Herfindahl-Hirschman (HHI) com nível de risco, Top 5 posições, concentração por classe (donut + barras horizontais), desvio do alvo por classe
- **Treemap SVG puro** (algoritmo Squarified) para visualização de concentração por ativo — sem dependências externas
- **Toggle diário/mensal** e seletor de período no gráfico de evolução

### Modal de Lançamento
- **Renda Fixa**: exibe apenas o campo "Valor Investido" — sem cotas
- **Ações, FIIs, BDRs**: campos de quantidade e preço unitário normais
- Labels e placeholders adaptados ao tipo de ativo selecionado

### Dados e automações
- **Asset seed** com UPSERT idempotente e endpoint admin em background
- **Sync semanal de dividendos de FIIs** via provedor de cotações: modo incremental com cursor e overlap de 30 dias; bootstrap de 5 anos via painel admin
- **Snapshots patrimoniais** com backfill manual/admin e recuperação automática quando o gráfico não encontra base histórica
- **Fallbacks em cascata** para Tesouro Direto, ativos internacionais e cripto
- **Scheduler APScheduler** com **8 jobs** para rotinas automáticas de atualização
- **Cache Redis** com invalidação automática após upsert de renda fixa/Tesouro Direto
- **Lock distribuído** em jobs de sync: previne execuções concorrentes (modelo `DividendsSyncJob`)

### Outras páginas
- **Transações** — histórico completo com filtros e gráfico de aportes mensais
- **Proventos** — histórico de dividendos e JCP com gráficos
- **IRPF** — apuração de ganho de capital (em construção)
- **Metas** — CRUD com progresso automático (em construção)

---

## Stack tecnológica

### Backend
| Tecnologia | Versão | Uso |
|---|---|---|
| Python | 3.12 | Linguagem base |
| FastAPI | ≥ 0.138.1 | Framework web async |
| SQLAlchemy | 2.x async | ORM |
| Alembic | 1.x | Migrations |
| PostgreSQL | 15 | Banco de dados |
| Redis | 7 | Cache |
| APScheduler | 3.x | 8 jobs agendados |
| SlowAPI | — | Rate limiter global |
| bcrypt | v5 | Hash de senhas |
| JWT | — | Auth com refresh token rotativo |

### Frontend
| Tecnologia | Versão | Uso |
|---|---|---|
| React | 19 | UI |
| TypeScript | 6.x | Tipagem |
| Vite | 8.1 | Build tool |
| TailwindCSS | 4.x | Utilitários CSS |
| Recharts | 3.x | Gráficos |
| React Query | 5.101 | Cache e estado servidor |
| Zustand | 5.x | Estado global |
| Lucide React | — | Ícones |
| Axios | — | HTTP client |

---

## Estrutura do projeto

```text
sig-v2/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   ├── models/
│   │   ├── routers/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── integrations/
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── store/
│   │   └── styles/
│   └── public/
├── docker-compose.yml
├── docker-compose.prod.yml
├── CHANGELOG.md
├── ROADMAP_SPRINTS.md
└── README.md
```

---

## Como rodar

### Com Docker

```bash
cp .env.example .env
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
| `DATABASE_URL` | URL PostgreSQL |
| `REDIS_URL` | URL Redis |
| `SECRET_KEY` | Chave JWT |
| `BRAPI_TOKEN` | Token do provedor de cotações |
| `SUPERADMIN_EMAIL` | E-mail do superadmin |
| `SUPERADMIN_PASSWORD` | Senha do superadmin |

---

## Análise de Gaps e Plano de Ação (02/07/2026)

📊 **Status:** 78% de completude funcional — 21 gaps identificados

Documentação completa de análise e plano de ação:

| Documento | Descrição |
|-----------|-----------|
| **[SUMARIO_EXECUTIVO.md](./SUMARIO_EXECUTIVO.md)** | ⭐ Comece por aqui — visão geral em 5 min |
| **[GAPS_ANALISE_COMPLETA.md](./GAPS_ANALISE_COMPLETA.md)** | Detalhamento de cada gap, impacto e recomendações |
| **[PLANO_ACAO_EXECUTAVEL.md](./PLANO_ACAO_EXECUTAVEL.md)** | 3 sprints de 8-12 semanas com tarefas concretas |
| **[MATRIZ_PRIORIZACAO.md](./MATRIZ_PRIORIZACAO.md)** | Timeline, prioridades e métricas de sucesso |

**Próximas prioridades (Sprint 1):**
- ✅ Índices PostgreSQL (-30-50% latência)
- ✅ Monitoramento de queries (pg_stat_statements)
- ✅ Cache Redis completo (dashboard instantâneo)
- ✅ Sprint 6A compliance (remover refs de APIs externas)

---

## Roadmap Histórico

Veja o roadmap original em [ROADMAP_SPRINTS.md](./ROADMAP_SPRINTS.md).

---

## Changelog

Veja o histórico completo em [CHANGELOG.md](./CHANGELOG.md).
