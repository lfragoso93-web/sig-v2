# SGI v2 — Sistema de Gestão de Investimentos

> Plataforma pessoal de acompanhamento de investimentos com backend FastAPI e frontend React.

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB)](https://reactjs.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D)](https://redis.io)

---

## Visão Geral

O SGI v2 é uma aplicação full-stack para controle de carteiras de investimento. Suporta Ações, FIIs, ETFs, BDRs, Criptomoedas, Renda Fixa e **Tesouro Direto** com cotação automática via múltiplas fontes.

---

## Funcionalidades

### Disponíveis
- **Carteiras**: criação, gestão e visão consolidada
- **Transações**: compra/venda com cálculo de preço médio automático
- **Posições**: controle de quantidade, PM e valor atual
- **Proventos**: registro e backfill histórico de dividendos/JCP
- **Rentabilidade**: KPIs de patrimônio, ganhos, retorno percentual por ativo e por classe
- **Tesouro Direto**: cotação com fallback em 4 camadas (BRAPI indicators → BRAPI list → Radar Opções → API TN)
- **Criptomoedas**: cotação BRL com normalização de 35 nomes completos (BITCOIN → BTC)
- **Câmbio**: cotação e histórico de pares (USD-BRL, EUR-BRL, etc.)
- **Metas financeiras**: CRUD com progresso calculado automaticamente
- **IRPF**: cálculo de ganho de capital para renda variável
- **Análise de carteira**: score de diversificação e concentração por setor
- **Catálogo de ativos**: seed automático de 2.259+ ativos via BRAPI (semanal)
- **Ativos internacionais**: BDR, ETF_INTL e STOCK via yfinance + Alpha Vantage
- **Design System CSS**: `globals.css` + `components.css` com tokens, classes utilitárias (`.table-dense`, `.badge`, `.page-container`, `.input-xs`) e layout responsivo consistente

### Em desenvolvimento (Sprint 5)
- Dashboard principal com resumo de patrimônio
- Gráfico de evolução patrimonial
- Telas de Metas, IRPF e Renda Fixa
- Listagem de ativos do catálogo

---

## Arquitetura

```
sig-v2/
├── backend/              # FastAPI + SQLAlchemy async
│   ├── app/
│   │   ├── core/         # config, database, security
│   │   ├── models/       # SQLAlchemy ORM
│   │   ├── routers/      # endpoints FastAPI
│   │   ├── services/     # lógica de negócio
│   │   ├── integrations/ # BRAPI, yfinance, Alpha Vantage, TN
│   │   └── schemas/      # Pydantic v2
│   ├── tests/
│   └── alembic/
├── frontend/             # React 18 + TypeScript + Vite
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   ├── services/
│   │   ├── hooks/
│   │   └── styles/       # globals.css + components.css (Design System)
├── docker-compose.yml
├── CHANGELOG.md
├── ROADMAP_SPRINTS.md
└── README.md
```

---

## Stack Tecnológica

| Camada | Tecnologia |
|--------|------------|
| Backend | FastAPI 0.115 + Python 3.12 |
| ORM | SQLAlchemy 2.x async |
| Banco | PostgreSQL 16 |
| Cache | Redis 7 |
| Migrações | Alembic |
| Frontend | React 18 + TypeScript + Vite |
| UI | Tailwind CSS + Design System próprio |
| Estado | TanStack Query (React Query) |
| Auth | JWT + refresh token rotativo |
| Scheduler | APScheduler |
| Cotações | BRAPI → Alpha Vantage → yfinance |
| Tesouro | BRAPI /indicators → /list → Radar Opções → API TN |
| Infra | Docker Compose + Nginx |

---

## Integrações de Cotação

### Tesouro Direto — 4 camadas de fallback
1. **BRAPI `/v2/treasury/indicators`** — somente com token válido (plano pago)
2. **BRAPI `/v2/treasury/list`** — plano free, sem token, sempre tentado
3. **Radar Opções API** — fallback externo gratuito
4. **API Tesouro Nacional** — fonte oficial, último recurso

### Demais ativos
- **Ações / FIIs / ETFs / BDRs**: BRAPI `/quote` com chunk de 20 tickers
- **Criptomoedas**: BRAPI `/v2/crypto` com normalização de nomes (35 moedas mapeadas)
- **Ativos internacionais**: yfinance com fallback Alpha Vantage
- **Câmbio**: BRAPI `/v2/currency` com fallback de formato `USD-BRL` ↔ `USDBRL`

---

## Como Rodar

### Pré-requisitos
- Docker e Docker Compose
- Arquivo `.env` configurado (ver `.env.example`)

### Subir o ambiente
```bash
docker-compose up -d
```

### Acessar
- **API**: http://localhost:8000
- **Docs Swagger**: http://localhost:8000/docs
- **Frontend**: http://localhost:3000

### Comandos úteis
```bash
# Rodar migrations
make migrate

# Criar nova migration
make migration msg="descricao"

# Rodar testes
make test

# Rebuild completo
make rebuild
```

---

## Variáveis de Ambiente

Ver `.env.example` para a lista completa. Principais:

| Variável | Descrição |
|----------|------------|
| `DATABASE_URL` | URL de conexão PostgreSQL |
| `REDIS_URL` | URL do Redis |
| `SECRET_KEY` | Chave JWT |
| `BRAPI_TOKEN` | Token BRAPI (opcional — melhora limites de cotação) |
| `ALPHA_VANTAGE_KEY` | Chave Alpha Vantage (opcional) |
| `SUPERADMIN_EMAIL` | E-mail do superadmin criado no boot |
| `SUPERADMIN_PASSWORD` | Senha do superadmin |

---

## Status do Projeto

| Sprint | Status | Período |
|--------|--------|----------|
| Sprint 1 — Fundação | ✅ Concluído | Abril 2026 |
| Sprint 2 — Core Financeiro | ✅ Concluído | Maio 2026 |
| Sprint 3 — Funcionalidades Avançadas | ✅ Concluído | Junho 2026 (1ª quinzena) |
| Sprint 4 — Catálogo de Ativos | ✅ Concluído | Junho 2026 (2ª quinzena) |
| Sprint 5 — Frontend Dashboard | 🔄 Em andamento | Junho–Julho 2026 |
| Sprint 6 — Produção e Qualidade | 📋 Planejado | Agosto 2026 |

Ver [ROADMAP_SPRINTS.md](./ROADMAP_SPRINTS.md) para detalhes por sprint.
Ver [CHANGELOG.md](./CHANGELOG.md) para histórico de mudanças.
