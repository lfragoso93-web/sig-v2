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
  └─> _calc_raw_positions()   — calcula posições brutas do histórico de transações
        └─> get_prices()       — quotes_service.py
              ├─> BRAPI        — ACAO, FII, ETF_NACIONAL, TESOURO_DIRETO, RENDA_FIXA, CRIPTO
              └─> yfinance     — STOCK, ETF_INTERNACIONAL
                    └─> dict {ticker: price}  — retorna None para tickers sem cotação (não faz fallback para preço médio)
```

> **Importante:** quando a cotação não está disponível, `current_price` retorna `null` no payload e o frontend exibe `—`. O sistema **nunca** usa o preço médio como substituto do preço atual.

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
│   ├── alembic/                # migrations
│   └── app/
│       ├── main.py             # ponto de entrada FastAPI, registro de routers
│       ├── core/               # config, database, deps, security
│       ├── models/             # SQLAlchemy ORM models
│       ├── schemas/            # Pydantic schemas
│       ├── routers/            # endpoints organizados por domínio
│       │   ├── auth.py
│       │   ├── portfolios.py   # CRUD carteiras + /summary + /positions
│       │   ├── transactions.py # CRUD transações (com migration inline de ticker VARCHAR(100))
│       │   ├── assets.py       # cadastro de ativos + busca BRAPI + /tesouro/search
│       │   ├── dividends.py
│       │   ├── proventos.py
│       │   ├── performance.py
│       │   ├── admin.py
│       │   └── [stubs: analysis, fixed_income, goals, irpf, fx]
│       ├── services/
│       │   ├── quotes_service.py   # orquestrador de cotações (BRAPI + yfinance + cripto)
│       │   ├── portfolio_service.py
│       │   └── [stubs: treasury_service]
│       └── integrations/
│           └── brapi.py            # fetch_quotes + _auth_headers
│
└── frontend/
    └── src/
        ├── components/
        │   ├── resume/
        │   │   └── PositionTable.tsx   # tabela de posições agrupadas por classe
        │   └── modals/
        │       └── AddTransactionModal.tsx
        ├── hooks/
        │   ├── usePortfolio.ts         # usePositions, usePortfolioSummary, toPositionGroups
        │   ├── useTransactions.ts
        │   ├── useTesouroSearch.ts     # busca títulos TD com debounce 500ms, min 2 chars
        │   └── useTreasuryPrice.ts
        ├── pages/
        │   ├── ResumePage.tsx          # dashboard principal
        │   ├── LancamentosPage.tsx     # modal de lançamento (Ação/FII/ETF/Stock/Tesouro)
        │   ├── TransacoesPage.tsx
        │   ├── ProventosPage.tsx
        │   ├── PatrimonioPage.tsx      # painel de patrimônio consolidado com filtro por classe
        │   └── RentabilidadePage.tsx
        └── services/
            └── api.ts                  # axios instance com interceptor de refresh token
```

---

## Status Real dos Módulos

### ✅ Funcionando

| Módulo | Detalhes |
|---|---|
| **Autenticação** | Cadastro, login JWT, refresh token, recuperação de senha |
| **Carteiras (Portfolios)** | CRUD completo, múltiplas carteiras por usuário |
| **Transações** | Compra/venda de todos os tipos de ativo, cálculo de preço médio FIFO |
| **Tesouro Direto** | Busca autocomplete (BRAPI), campos específicos (indexador, taxa, vencimento, PU), salva com ticker slug até 100 chars |
| **Posições** | Agrupadas por classe de ativo, preço médio, cotação atual (ou `—` quando indisponível), resultado absoluto e % |
| **Cotações** | BRAPI para ativos nacionais; yfinance para STOCK/ETF_INT; BRAPI `/v2/crypto` para cripto em BRL |
| **Resumo (Dashboard)** | Patrimônio total, total investido, lucro, variação, proventos 12m |
| **Proventos** | Cadastro manual, histórico, consolidação |
| **Eventos Corporativos** | Grupamento, desdobramento, bonificação com ajuste de posição |
| **Rentabilidade** | Retorno por carteira (absoluto e %) |
| **Admin** | Painel de usuários e configurações (is_superuser) |
| **PatrimonioPage** | Conectada ao `selectedPortfolioId` do store; KPIs, alocação por classe, donut chart e tabela de posições; filtro de classe interativo |

### 🚧 Parcialmente Implementado

| Módulo | O que existe | O que falta |
|---|---|---|
| **IRPF** | Model + router stub | Service de apuração mensal, cálculo de DARF, exportação PDF/CSV |
| **Análise IA (Gemini)** | Router stub | `analysis_service.py`, prompts, integração Gemini, tela frontend |
| **Renda Fixa** | Model + router stub | CRUD completo backend + tela frontend |
| **Metas (Goals)** | Model criado | CRUD backend + tela frontend com progresso |
| **Benchmarks** | Estrutura preparada | Integração CDI/IBOV/IPCA na tela de Rentabilidade |
| **FX (câmbio)** | Router básico | USD/BRL em tempo real para consolidar patrimônio em BRL |
| **Tesouro Direto — edição/exclusão** | Cadastro funcional | Editar e excluir títulos; `treasury_service.py` quase vazio |

### 🔧 Dívidas Técnicas Conhecidas

| Item | Arquivo(s) | Ação |
|---|---|---|
| Arquivos duplicados de páginas | `Resumo.tsx` vs `ResumePage.tsx`, `Transacoes.tsx` vs `TransacoesPage.tsx`, etc. | Consolidar, remover legados |
| `treasury_service.py` quase vazio | `services/treasury_service.py` | Implementar lógica de negócio |
| Testes automatizados | — | Criar suite pytest no backend |
| Migration Alembic formal para `ticker VARCHAR(100)` | `transactions.py` tem migration inline | Criar migration Alembic real |

---

## Bugs Corrigidos (histórico)

Registro de todos os bugs identificados e corrigidos durante o desenvolvimento:

### Sessão Junho 2026

| # | Bug | Causa | Correção |
|---|---|---|---|
| 1 | **P. Atual = P. Médio na tabela de posições** | `prices.get(ticker) or avg_price` usava avg como fallback quando cotação falhava | `current_price = None` quando ausente; `result_abs = 0` sem cotação; frontend exibe `—` |
| 2 | **Tesouro Direto não salvava** | Coluna `ticker VARCHAR(20)` truncava slugs como `tesouro-renda-aposentadoria-extra-01122065` (46 chars) | `String(100)` no model + migration inline `ALTER COLUMN ticker TYPE VARCHAR(100)` |
| 3 | **Tesouro Renda+ não aparecia no autocomplete** | Interface `TreasuryItem` não tinha campo `slug`; `applyTDSuggestion` fazia `(item as any).slug` → `undefined` → ticker errado | Adicionado `slug: string \| null` na interface; debounce 700ms→500ms; mínimo 3 chars→2 chars |
| 4 | **Cripto com valor errado** | `CRIPTO` estava em `INTL_TYPES` → cotação via yfinance em USD; frontend exibia em BRL | Movido para `BR_TYPES`; cripto via `_fetch_brapi_crypto()` separado (BRAPI `/v2/crypto?currency=BRL`) |
| 5 | **Crash `Cannot read properties of undefined (reading 'map')`** | `PositionTable` usava `group.items` mas `PositionGroup` do hook usa `group.positions` | `PositionTable` importa `PositionGroup` diretamente de `usePortfolio.ts`; usa `group.positions` |
| 6 | **Nome correto do ativo não aparecia no autocomplete** | Lógica de label display no AddTransactionModal não usava o campo `name` retornado pelo backend | Corrigido para usar `item.name` quando disponível |
| 7 | **PatrimonioPage não carregava dados** | `portfolioId` caia para `portfolios?.[0]?.id ?? 0` antes da carteira ser selecionada; `usePositions(0)` disparava com ID inválido | `PatrimonioPage` passa a usar `selectedPortfolioId` do store Zustand diretamente, sem fallback; exibe empty state se nenhuma carteira selecionada |
| 8 | **PatrimonioPage tinha seletor de carteira duplicado** | A página tinha um switcher de carteiras próprio, redundante com o seletor global do header | Removido o seletor da página; toda navegação de carteiras usa exclusivamente o header global |

---

## Modelos de Dados

| Model | Arquivo | Descrição |
|---|---|---|
| `User` | `user.py` | Usuário do sistema |
| `Portfolio` | `portfolio.py` | Carteira de investimentos |
| `Asset` | `asset.py` | Ativo (ação, FII, cripto etc.) |
| `AssetPrice` | `asset_price.py` | Histórico de preços |
| `Transaction` | `transaction.py` | Transações (ticker até 100 chars) |
| `Dividend` | `dividend.py` | Proventos recebidos |
| `CorporateEvent` | `corporate_event.py` | Eventos corporativos |
| `FixedIncome` | `fixed_income.py` | Renda fixa |
| `Treasury` | `treasury.py` | Títulos do Tesouro Direto |
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
| GET | `/assets/tesouro/search?q=` | ✅ busca títulos TD via BRAPI |

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

> **Normalização:** aliases como `ACAO`, `ETF_INT`, `TESOURO`, `CRIPTO` são normalizados em `_normalize_type()` no `portfolios.py`.

---

## Frontend — Páginas e Rotas

| Rota | Página | Status |
|---|---|---|
| `/` | `Landing.tsx` | ✅ |
| `/login` | `Login.tsx` | ✅ |
| `/register` | `Register.tsx` | ✅ |
| `/esqueceu-senha` | `EsqueceuSenha.tsx` | ✅ |
| `/app/resumo` | `ResumePage.tsx` | ✅ Dashboard com tabela de posições agrupadas |
| `/app/lancamentos` | `LancamentosPage.tsx` | ✅ Modal para todos os tipos de ativo incl. Tesouro |
| `/app/transacoes` | `TransacoesPage.tsx` | ✅ |
| `/app/proventos` | `ProventosPage.tsx` | ✅ |
| `/app/rentabilidade` | `RentabilidadePage.tsx` | ✅ |
| `/app/configuracoes` | `Configuracoes.tsx` | ✅ |
| `/app/patrimonio` | `PatrimonioPage.tsx` | ✅ KPIs, alocação por classe, donut, posições filtradas |
| `/app/irpf` | `IRPFPage.tsx` | 🚧 Stub |
| `/app/analise` | `AnalisePage.tsx` | 🚧 Stub |
| `/app/metas` | `MetasPage.tsx` | 🚧 Stub |

---

## Autenticação e Segurança

- **JWT**: tokens stateless com expiração configurável
- **Bcrypt**: hash de senhas
- **Refresh Token**: renovação automática via interceptor Axios
- **CORS**: configurado via `ALLOWED_ORIGINS`
- **Isolamento de dados**: todos os endpoints filtram por `user_id` do token
- **Admin routes**: protegidas por `is_superuser`

---

## Docker e Infra

### Desenvolvimento

```bash
docker compose up -d --build
```

Serviços: `frontend` (5173) · `backend` (8000) · `postgres` (5432) · `nginx` (80)

### Produção

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

### Migrations

O `entrypoint.sh` executa `alembic upgrade head` automaticamente ao subir.

```bash
# Criar nova migration
docker compose exec backend alembic revision --autogenerate -m "descricao"
docker compose exec backend alembic upgrade head
```

---

## Guia de Continuação

> Use esta seção como ponto de partida em cada nova sessão de desenvolvimento.

### Próximos passos priorizados

#### 🔴 Alta Prioridade

1. **Criar migration Alembic formal para `ticker VARCHAR(100)`**
   - Atualmente existe apenas uma migration inline em `transactions.py` (`_ensure_migrations`)
   - Criar `alembic revision --autogenerate -m "increase_ticker_length"` e remover a migration inline
   - Arquivo: `backend/alembic/versions/`

2. **Renda Fixa — CRUD completo**
   - Backend: `routers/fixed_income.py` é stub (77 bytes) — implementar endpoints CRUD
   - Service: `services/fixed_income_service.py` não existe — criar
   - Frontend: tela de cadastro e listagem de RF, integrar ao modal de lançamentos
   - Modelo já existe: `models/fixed_income.py`

3. **Tesouro Direto — edição e exclusão**
   - Cadastro via modal já funciona ✅
   - Falta: editar e excluir títulos na tabela de posições
   - Backend: `treasury_service.py` está quase vazio — implementar `get`, `update`, `delete`

#### 🟡 Média Prioridade

4. **Benchmarks na tela de Rentabilidade**
   - Integrar CDI (API do Banco Central), IBOV e IPCA
   - Exibir gráfico comparativo na `RentabilidadePage.tsx`
   - Hook `usePerformance.ts` já existe e busca `/performance`

5. **Análise IA (Gemini)**
   - Criar `services/analysis_service.py` com prompts de análise de carteira
   - Conectar `GEMINI_API_KEY` do `.env`
   - Implementar `routers/analysis.py` (stub com 78 bytes)
   - Página `AnalisePage.tsx` já existe como stub

6. **Metas (Goals)**
   - Model `goal.py` existe
   - `routers/goals.py` é stub (77 bytes) — implementar CRUD
   - Frontend: `MetasPage.tsx` stub — implementar tela com progresso visual

7. **FX (câmbio)**
   - `routers/fx.py` tem implementação básica (324 bytes)
   - Completar para buscar USD/BRL em tempo real via BRAPI ou BCB
   - Usar na consolidação de patrimônio para converter ativos em USD para BRL

#### 🟢 Baixa Prioridade / Qualidade

8. **Limpeza de arquivos duplicados**
   - Existem pares legados: `Resumo.tsx` / `ResumePage.tsx`, `Transacoes.tsx` / `TransacoesPage.tsx`, etc.
   - Verificar qual versão está ativa no router, remover a obsoleta

9. **IRPF**
   - Módulo mais complexo — model e router stub existem
   - Implementar: apuração mensal, cálculo de ganho de capital, isenções (ações até R$20k/mês), DARFs, exportação

10. **Testes automatizados**
    - Criar `backend/tests/` com pytest
    - Prioridade: `quotes_service`, `portfolios` (cálculo de posições), `transactions`

11. **Exportação de dados**
    - CSV/Excel de transações e posições
    - Botão na `TransacoesPage.tsx`

### Contexto técnico importante para próximas sessões

**Padrão de cotações:**
- `get_prices()` retorna `dict[str, float]` — tickers ausentes = cotação indisponível
- Nunca usar `prices.get(ticker) or avg_price` — isso mascarava bugs (já corrigido)
- `current_price: Optional[float]` no schema e no frontend

**Padrão de posições:**
- Backend retorna lista flat de `PositionItem` no endpoint `/positions`
- `toPositionGroups()` em `usePortfolio.ts` agrupa por `asset_type` no frontend
- `PositionGroup.positions` (não `.items`) é o campo com os itens do grupo

**Tesouro Direto:**
- Ticker salvo = slug da BRAPI (ex: `TESOURO-SELIC-01032031`) — até 100 chars
- `useTesouroSearch` busca via `/assets/tesouro/search?q=` com debounce 500ms, mínimo 2 chars
- Interface `TreasuryItem` inclui campo `slug` (obrigatório para o submit funcionar)

**Cripto:**
- Cotações via BRAPI `/api/v2/crypto?coin={TICKER}&currency=BRL` — retorna em BRL diretamente
- `asset_type = CRIPTO` → vai para `_fetch_brapi_crypto()`, não para yfinance

**Seleção de carteira:**
- `selectedPortfolioId` vive no store Zustand (`useAppStore`)
- Todas as páginas devem ler `selectedPortfolioId` do store — sem fallback para `portfolios[0]`
- Se `portfolioId` for `null`, exibir empty state orientando o usuário a selecionar uma carteira no header
