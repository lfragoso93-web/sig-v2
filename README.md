# SIG v2 — Sistema de Investimentos Gerenciado

> Plataforma full-stack containerizada para gestão de carteiras de investimentos, com suporte a múltiplas carteiras, cotações automáticas, proventos, eventos corporativos e módulo de IRPF.

**Última atualização da documentação:** Junho 2026

---

## Índice

- [Visão Geral](#visão-geral)
- [Stack Tecnológico](#stack-tecnológico)
- [Arquitetura](#arquitetura)
- [Início Rápido](#início-rápido)
- [Desenvolvimento Local](#desenvolvimento-local)
- [Variáveis de Ambiente](#variáveis-de-ambiente)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Status Real dos Módulos](#status-real-dos-módulos)
- [Bugs Corrigidos (histórico)](#bugs-corrigidos-histórico)
- [Modelos de Dados](#modelos-de-dados)
- [API — Endpoints](#api--endpoints)
- [Tipos de Ativos Suportados](#tipos-de-ativos-suportados)
- [Frontend — Páginas e Rotas](#frontend--páginas-e-rotas)
- [Autenticação e Segurança](#autenticação-e-segurança)
- [Docker e Infra](#docker-e-infra)
- [Análise de Qualidade do Código](#análise-de-qualidade-do-código)
- [Guia de Continuação](#guia-de-continuação)

---

## Visão Geral

O **SIG v2** é uma reescrita completa do sistema SIG, projetada para suportar múltiplas carteiras por usuário, integração com IA (Google Gemini), cotações automáticas via BRAPI e Yahoo Finance, gestão de proventos, eventos corporativos (grupamentos, bonificações, desdobramentos) e geração de dados para IRPF.

**Componentes:**
- **Backend**: API REST em FastAPI (Python 3.12) com banco PostgreSQL
- **Frontend**: SPA em React 18 + Vite + TypeScript + Tailwind CSS
- **Infra**: Docker Compose para desenvolvimento e produção

---

## Stack Tecnológico

| Camada | Tecnologia | Versão |
|---|---|---|
| Frontend | React + Vite + TypeScript | React 18, Vite 5 |
| Estilo | Tailwind CSS | v3 |
| Estado global | Zustand | — |
| Roteamento | React Router DOM | v6 |
| HTTP Client | Axios | — |
| Backend | FastAPI (Python) | Python 3.12 |
| ORM | SQLAlchemy (async) | — |
| Banco de dados | PostgreSQL | v16 |
| Cotações nacionais | BRAPI | — |
| Cotações internacionais | yfinance (Yahoo Finance) | — |
| Cotações cripto | BRAPI `/api/v2/crypto` (BRL) | — |
| Integração IA | Google Gemini API | — |
| Infra | Docker + Docker Compose + Nginx | — |

---

## Arquitetura

```
Browser
  └─> Nginx (porta 80)
        ├─> /          ──────────> Frontend (React SPA)
        └─> /api/v1/*  ──────────> FastAPI Backend
                                      ├─> PostgreSQL (dados persistentes)
                                      ├─> BRAPI (ações, FIIs, ETFs nacionais, cripto BRL)
                                      └─> Yahoo Finance (stocks, ETFs internacionais)
```

### Fluxo de Cotações

```
GET /portfolios/{id}/positions
  └─> portfolio_service.calc_positions()  — calcula posições via Preço Médio Ponderado
        └─> quotes_service.get_prices()   — busca cotações em paralelo (asyncio.gather)
              ├─> BRAPI                   — ACAO, FII, ETF_NACIONAL, TESOURO_DIRETO, RENDA_FIXA
              ├─> BRAPI /v2/crypto        — CRIPTO em BRL (paralelo via asyncio.gather)
              └─> yfinance                — STOCK, ETF_INTERNACIONAL (ThreadPoolExecutor global)
                    └─> dict {ticker: price}  — tickers ausentes = cotação indisponível
```

> **Importante:** quando a cotação não está disponível, `current_price` retorna `null` no payload e o frontend exibe `—`. O sistema **nunca** usa o preço médio como substituto do preço atual.

### Método de Custo de Aquisição

O sistema usa **Preço Médio Ponderado** para calcular o custo de aquisição das posições:

```
avg_price = total_cost / qty_total
```

A cada venda, o custo médio é recalculado sobre o saldo remanescente:

```
total_cost -= avg_price * qty_vendida
```

> **Por que Preço Médio Ponderado e não FIFO?**
> A Receita Federal brasileira aceita os dois métodos, mas **quase todas as corretoras brasileiras e sistemas de controle patrimonial usam Preço Médio Ponderado**. O FIFO é obrigatório apenas para commodities físicas. O Preço Médio tende a ser mais favorável ao investidor no curto prazo (menor IR mensal) e é mais simples de manter de forma consistente ao longo do tempo. Quando o módulo de IRPF for implementado, ele **deve** usar este mesmo método de forma consistente para não gerar divergências.

---

## Início Rápido

```bash
# 1. Clone
git clone https://github.com/lfragoso93-web/sig-v2
cd sig-v2

# 2. Configure as variáveis
cp .env.example .env
# Edite .env: POSTGRES_PASSWORD, SECRET_KEY, BRAPI_TOKEN

# 3. Suba os containers
docker compose up -d --build

# 4. Acesse
# Frontend:  http://localhost
# API Docs:  http://localhost/api/v1/docs
```

---

## Desenvolvimento Local

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# Swagger: http://localhost:8000/docs
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# http://localhost:5173
```

### Makefile

```bash
make up        # docker compose up -d --build
make down      # docker compose down
make logs      # docker compose logs -f
make restart   # down + up
make migrate   # alembic upgrade head (dentro do container)
```

---

## Variáveis de Ambiente

| Variável | Descrição | Obrigatória |
|---|---|---|
| `POSTGRES_DB` | Nome do banco | Sim |
| `POSTGRES_USER` | Usuário do banco | Sim |
| `POSTGRES_PASSWORD` | Senha do banco | Sim |
| `SECRET_KEY` | Chave secreta JWT | Sim |
| `BRAPI_TOKEN` | Token BRAPI | Não (limite menor sem token) |
| `GEMINI_API_KEY` | Chave Google Gemini | Não |
| `APP_PORT` | Porta de acesso (padrão: 80) | Não |
| `ALLOWED_ORIGINS` | Origens CORS | Não |

---

## Estrutura do Projeto

```
sig-v2/
├── .env.example
├── docker-compose.yml
├── docker-compose.prod.yml
├── Makefile
├── README.md
│
├── backend/
│   ├── Dockerfile
│   ├── entrypoint.sh           # roda alembic upgrade head antes de iniciar
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/                # migrations (002 = ticker VARCHAR(100))
│   └── app/
│       ├── main.py
│       ├── core/
│       ├── models/
│       ├── schemas/
│       ├── routers/
│       │   ├── portfolios.py   # ✅ só HTTP — lógica delegada ao portfolio_service
│       │   ├── transactions.py # ✅ limpo
│       │   ├── assets.py
│       │   ├── dividends.py
│       │   ├── proventos.py
│       │   ├── performance.py
│       │   ├── admin.py
│       │   └── [stubs: analysis, fixed_income, goals, irpf, fx]
│       ├── services/
│       │   ├── quotes_service.py   # ✅ ThreadPoolExecutor global + cripto paralelo
│       │   ├── portfolio_service.py # ✅ contém calc_positions + sum_dividends
│       │   └── [stubs: treasury_service]
│       └── integrations/
│           └── brapi.py
│
└── frontend/
    └── src/
        ├── pages/
        │   ├── ResumePage.tsx       # ✅ ativo
        │   ├── ProventosPage.tsx    # ✅ ativo
        │   ├── RentabilidadePage.tsx # ✅ ativo
        │   ├── Transacoes.tsx       # ✅ ativo
        │   ├── Resumo.tsx           # ⚠️ obsoleto (stub vazio)
        │   ├── Proventos.tsx        # ⚠️ obsoleto (stub vazio)
        │   ├── Rentabilidade.tsx    # ⚠️ obsoleto (stub vazio)
        │   └── TransacoesPage.tsx   # ⚠️ obsoleto (stub vazio)
        └── services/
            └── api.ts               # ⚠️ JWT em localStorage (aceito para uso privado)
```

---

## Status Real dos Módulos

### ✅ Funcionando

| Módulo | Detalhes |
|---|---|
| **Autenticação** | Cadastro, login JWT, refresh token, recuperação de senha |
| **Carteiras (Portfolios)** | CRUD completo, múltiplas carteiras por usuário |
| **Transações** | Compra/venda de todos os tipos de ativo, Preço Médio Ponderado |
| **Tesouro Direto** | Busca autocomplete (BRAPI), campos específicos, salva com ticker slug até 100 chars |
| **Posições** | Agrupadas por classe, preço médio ponderado, cotação atual (ou `—`), resultado absoluto e % |
| **Cotações** | BRAPI (nacionais); yfinance (STOCK/ETF_INT); BRAPI `/v2/crypto` (cripto BRL) — todas em paralelo |
| **Resumo (Dashboard)** | Patrimônio total, total investido, lucro, variação, proventos 12m |
| **Proventos** | Cadastro manual, histórico, consolidação |
| **Eventos Corporativos** | Grupamento, desdobramento, bonificação |
| **Rentabilidade** | Retorno por carteira (absoluto e %) |
| **Admin** | Painel de usuários e configurações |
| **PatrimonioPage** | KPIs, alocação por classe, donut chart, tabela de posições com filtro |

### 🚧 Parcialmente Implementado

| Módulo | O que existe | O que falta |
|---|---|---|
| **IRPF** | Model + router stub | Apuração, cálculo DARF, exportação |
| **Análise IA (Gemini)** | Router stub | `analysis_service.py`, prompts, tela |
| **Renda Fixa** | Model + router stub | CRUD backend + tela frontend |
| **Metas (Goals)** | Model criado | CRUD backend + tela |
| **Benchmarks** | Estrutura preparada | Integração CDI/IBOV/IPCA/IFIX |
| **FX (câmbio)** | Router básico | USD/BRL em tempo real |
| **Tesouro Direto — edição/exclusão** | Cadastro funcional | Editar/excluir; `treasury_service.py` quase vazio |

### 🔧 Dívidas Técnicas Restantes

| Item | Arquivo(s) | Ação |
|---|---|---|
| Testes automatizados (cobertura 0%) | — | Criar suite pytest; meta 70% nos serviços financeiros |
| JWT em localStorage | `frontend/src/services/api.ts` | Migrar para HttpOnly Cookie antes de SaaS |
| Cache em memória não escala multi-worker | `quotes_service.py` | Migrar para Redis (futuro) |
| Arquivos duplicados (stubs vazios) | `Resumo.tsx`, `Proventos.tsx`, etc. | Deletar via `git rm` após confirmar que não há imports |

---

## Bugs Corrigidos (histórico)

### Sessão Junho 2026

| # | Bug | Causa | Correção |
|---|---|---|---|
| 1 | **P. Atual = P. Médio na tabela de posições** | `prices.get(ticker) or avg_price` usava avg como fallback | `current_price = None`; frontend exibe `—` |
| 2 | **Tesouro Direto não salvava** | `ticker VARCHAR(20)` truncava slugs longos | `String(100)` + migration 002 |
| 3 | **Tesouro Renda+ sumia no autocomplete** | Interface sem campo `slug` | Adicionado `slug: string \| null`; debounce 500ms; mín. 2 chars |
| 4 | **Cripto com valor errado** | `CRIPTO` em `INTL_TYPES` → yfinance USD | Movido para `BR_TYPES`; `_fetch_brapi_crypto()` BRL |
| 5 | **Crash `Cannot read .map`** | `group.items` vs `group.positions` | `PositionTable` usa `group.positions` |
| 6 | **Nome do ativo ausente no autocomplete** | Campo `name` ignorado | Corrigido para usar `item.name` |
| 7 | **PatrimonioPage não carregava** | `usePositions(0)` com ID inválido | Usa `selectedPortfolioId` do store Zustand |
| 8 | **Seletor de carteira duplicado** | Switcher próprio na página além do header | Removido da página |

---

## Modelos de Dados

| Model | Arquivo | Descrição |
|---|---|---|
| `User` | `user.py` | Usuário do sistema |
| `Portfolio` | `portfolio.py` | Carteira de investimentos |
| `Asset` | `asset.py` | Ativo |
| `AssetPrice` | `asset_price.py` | Histórico de preços |
| `Transaction` | `transaction.py` | Transações (ticker até 100 chars) |
| `Dividend` | `dividend.py` | Proventos recebidos |
| `CorporateEvent` | `corporate_event.py` | Eventos corporativos |
| `FixedIncome` | `fixed_income.py` | Renda fixa |
| `Treasury` | `treasury.py` | Tesouro Direto |
| `Goal` | `goal.py` | Metas financeiras |
| `IRPF` | `irpf.py` | Dados para IR |
| `SystemConfig` | `system_config.py` | Configurações do sistema |

---

## API — Endpoints

Base URL: `http://localhost/api/v1`

### Autenticação
| Método | Rota | Status |
|---|---|---|
| POST | `/auth/register` | ✅ |
| POST | `/auth/login` | ✅ |
| POST | `/auth/refresh` | ✅ |
| POST | `/auth/forgot-password` | ✅ |
| POST | `/auth/reset-password` | ✅ |

### Carteiras
| Método | Rota | Status |
|---|---|---|
| GET | `/portfolios` | ✅ |
| POST | `/portfolios` | ✅ |
| PUT | `/portfolios/{id}` | ✅ |
| DELETE | `/portfolios/{id}` | ✅ |
| GET | `/portfolios/{id}/summary` | ✅ |
| GET | `/portfolios/{id}/positions` | ✅ |
| GET | `/portfolios/{id}/transactions` | ✅ |
| POST | `/portfolios/{id}/transactions` | ✅ |
| DELETE | `/portfolios/{id}/transactions/{tx_id}` | ✅ |

### Ativos
| Método | Rota | Status |
|---|---|---|
| GET | `/assets` | ✅ |
| POST | `/assets` | ✅ |
| GET | `/assets/search?q=` | ✅ |
| GET | `/assets/tesouro/search?q=` | ✅ |

### Proventos / Dividendos
| Método | Rota | Status |
|---|---|---|
| GET/POST | `/proventos` | ✅ |
| POST | `/proventos/sync` | ✅ |
| GET/POST | `/dividends` | ✅ |

### Performance
| Método | Rota | Status |
|---|---|---|
| GET | `/performance` | ✅ |
| GET | `/performance/{portfolio_id}` | ✅ |

### Stubs (não implementados)
| Rota | Módulo |
|---|---|
| `/analysis/*` | Análise IA Gemini |
| `/irpf/*` | IRPF |
| `/fixed-income/*` | Renda Fixa |
| `/goals/*` | Metas |

---

## Tipos de Ativos Suportados

| Tipo interno | Label exibido | Fonte de cotação | Moeda |
|---|---|---|---|
| `ACAO_NACIONAL` | Ações | BRAPI | BRL |
| `FII` | FIIs | BRAPI | BRL |
| `ETF_NACIONAL` | ETFs Nacionais | BRAPI | BRL |
| `TESOURO_DIRETO` | Tesouro Direto | BRAPI | BRL |
| `RENDA_FIXA` | Renda Fixa | — (manual) | BRL |
| `STOCK` | Stocks | yfinance | USD |
| `ETF_INTERNACIONAL` | ETFs Internacionais | yfinance | USD |
| `CRIPTO` | Criptomoedas | BRAPI `/v2/crypto?currency=BRL` | BRL |

---

## Frontend — Páginas e Rotas

| Rota | Página | Status |
|---|---|---|
| `/` | `Landing.tsx` | ✅ |
| `/login` | `LoginPage.tsx` | ✅ |
| `/register` | `RegisterPage.tsx` | ✅ |
| `/carteira` | `ResumePage.tsx` | ✅ |
| `/carteira/lancamentos` | `LancamentosPage.tsx` | ✅ |
| `/carteira/transacoes` | `Transacoes.tsx` | ✅ |
| `/carteira/proventos` | `ProventosPage.tsx` | ✅ |
| `/carteira/rentabilidade` | `RentabilidadePage.tsx` | ✅ |
| `/carteira/configuracoes` | `Configuracoes.tsx` | ✅ |
| `/patrimonio` | `PatrimonioPage.tsx` | ✅ |
| `/irpf` | `IRPFPage.tsx` | 🚧 Stub |
| `/analise` | `AnalisePage.tsx` | 🚧 Stub |
| `/metas` | `MetasPage.tsx` | 🚧 Stub |

---

## Autenticação e Segurança

- **JWT**: tokens stateless com expiração configurável
- **Bcrypt**: hash de senhas
- **Refresh Token**: renovação automática via interceptor Axios
- **CORS**: configurado via `ALLOWED_ORIGINS`
- **Isolamento de dados**: todos os endpoints filtram por `user_id` do token
- **Admin routes**: protegidas por `is_superuser`
- **⚠️ JWT em localStorage**: aceito para uso privado/pessoal. Migrar para HttpOnly Cookie antes de exposição pública

---

## Docker e Infra

```bash
docker compose up -d --build  # desenvolvimento
docker compose -f docker-compose.prod.yml up -d --build  # produção
```

Serviços: `frontend` (5173) · `backend` (8000) · `postgres` (5432) · `nginx` (80)

```bash
# Migrations
docker compose exec backend alembic revision --autogenerate -m "descricao"
docker compose exec backend alembic upgrade head
```

---

## Análise de Qualidade do Código

| Área | Nota |
|---|---|
| Arquitetura | 8,5/10 |
| Modelagem Financeira | 8,5/10 |
| Qualidade do Código | 8/10 ✅ |
| Segurança | 7/10 |
| Escalabilidade | 7,5/10 ✅ |
| **Testabilidade** | **3/10** ⚠️ maior risco |
| Maturidade Geral | 8/10 ✅ |

---

## Guia de Continuação

> Use esta seção como ponto de partida em cada nova sessão de desenvolvimento.

---

### Roadmap — 4 Fases

#### ✅ Fase 1 — Fundação (CONCLUÍDA em Junho 2026)

| Item | Status | Commit |
|---|---|---|
| Mover lógica de `portfolios.py` → `portfolio_service.py` | ✅ | `8963106` |
| `ThreadPoolExecutor` global para yfinance | ✅ | `c5a8d93` |
| `asyncio.gather()` para cripto paralelo | ✅ | `c5a8d93` |
| Migration Alembic formal `ticker VARCHAR(100)` | ✅ | já existia (`002`) |
| Limpeza de arquivos duplicados frontend | ✅ | `98b24e2` |
| **Testes automatizados (pytest)** | ⏳ **PENDENTE** | — |

> ⚠️ **A suite de testes é o único item da Fase 1 ainda pendente.** É a maior dívida técnica do projeto. Implementar antes de avançar para a Fase 2.

---

#### 🟡 Fase 2 — Core financeiro completo

1. **Suite pytest** — `backend/tests/` com fixtures SQLite async; cobertura alvo: 70% nos serviços financeiros
2. **Renda Fixa** — CRUD completo (`fixed_income_service.py`) + tela frontend
3. **Tesouro Direto — edição e exclusão** — completar `treasury_service.py`
4. **FX (câmbio)** — USD/BRL em tempo real; usar na `PatrimonioPage` para BRL correto
5. **Benchmarks CDI/IPCA/IBOV/IFIX** — tela de Rentabilidade com gráfico comparativo

---

#### 🟢 Fase 3 — Valor estratégico

6. **Metas financeiras** — CRUD + `MetasPage.tsx` com barra de progresso
7. **IRPF** — apuração mensal (Preço Médio Ponderado), isenções ações ≤R$20k/mês, DARF, exportação CSV
8. **Exportação de dados** — CSV/Excel de transações e posições
9. **Engine de posições materializadas** — tabela `portfolio_positions` atualizada por evento

---

#### 🔵 Fase 4 — Diferencial competitivo

10. **Análise IA (Gemini)** — `analysis_service.py`, prompts, `AnalisePage.tsx`
11. **Importação via CSV** — histórico de transações de corretoras
12. **HttpOnly Cookie** — migrar JWT de `localStorage` (obrigatório antes de SaaS)
13. **Cache Redis** — substituir `_cache = {}` por Redis com TTL

---

### Contexto técnico importante para próximas sessões

**Método de custo de aquisição:** Preço Médio Ponderado. `avg_price = total_cost / qty_total`. A cada venda: `total_cost -= avg_price * qty_vendida`. Módulo de IRPF **deve** usar este mesmo método.

**Padrão de cotações:** `get_prices()` retorna `dict[str, float]` — tickers ausentes = cotação indisponível. Nunca usar `prices.get(ticker) or avg_price`.

**Padrão de posições:** backend retorna lista flat de `PositionItem`; `toPositionGroups()` em `usePortfolio.ts` agrupa por `asset_type`; campo é `group.positions` (não `.items`).

**Tesouro Direto:** ticker = slug BRAPI (ex: `TESOURO-SELIC-01032031`); até 100 chars; `TreasuryItem` tem campo `slug` obrigatório.

**Cripto:** via BRAPI `/api/v2/crypto?coin={TICKER}&currency=BRL` → BRL direto. `asset_type = CRIPTO` → `_fetch_brapi_crypto()`, nunca yfinance.

**Seleção de carteira:** `selectedPortfolioId` no store Zustand (`useAppStore`). Todas as páginas leem do store. Se `null`, exibir empty state.
