# SIG v2 — Sistema de Investimentos Gerenciado

> Plataforma full-stack containerizada para gestão de carteiras de investimentos, com suporte a múltiplas carteiras, cotações automáticas, proventos, eventos corporativos e módulo de IRPF.

**Última atualização da documentação:** 15 Jun 2026 — pós-Sprint 4

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

> **Importante:** quando a cotação não está disponível, `current_price`, `current_value`, `result_abs` e `result_pct` retornam `null` no payload e o frontend exibe `—`. O sistema **nunca** usa o preço médio como substituto do preço atual.

### Método de Custo de Aquisição

O sistema usa **Preço Médio Ponderado** para calcular o custo de aquisição das posições:

```
avg_price = total_cost / qty_total
```

Regras aplicadas pelo `portfolio_service.py`:

| Evento | Comportamento |
|---|---|
| Compra | PM recalculado: `(custo_atual + qty*preco + fees) / (qty_atual + qty)` |
| Venda | PM **invariante**. `total_cost -= avg_price * qty_vendida`. `qty` diminui. |
| `fees` de venda | **NÃO** entram no PM. Afetam apenas lucro realizado. |
| Posição zerada | `qty <= 1e-9` → some da carteira (vale para renda variável **e** Tesouro Direto). |
| Sem cotação | `current_price=None`, `current_value=None`, `result_abs=None`, `result_pct=None`. Nunca usar PM como fallback. |

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
make test      # pytest com requirements-test.txt (dentro do container)
make lint      # ruff check app/
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
├── Makefile                        # targets: up, down, logs, restart, migrate, test, lint
├── README.md
├── CHANGELOG.md
├── ROADMAP_SPRINTS.md
│
├── backend/
│   ├── Dockerfile
│   ├── entrypoint.sh
│   ├── requirements.txt
│   ├── requirements-test.txt          # pytest + pytest-asyncio + aiosqlite
│   ├── pytest.ini                     # asyncio_mode=auto
│   ├── alembic.ini
│   ├── alembic/
│   ├── tests/                         # ✅ suite pytest (Junho 2026)
│   │   ├── conftest.py                  # fixtures SQLite async: engine, db, user, portfolio
│   │   ├── test_portfolio_service.py    # PM, posições, CRUD carteiras (~23 testes)
│   │   ├── test_transaction_service.py  # _calc_average_price (8 testes)
│   │   ├── test_auth_service.py         # hash/verify senha, JWT (6 testes)
│   │   ├── test_quotes_service.py       # roteamento BRAPI/yfinance/cripto (5 testes)
│   │   └── test_dividend_service.py     # sum_dividends, cutoff, isolamento (4 testes)
│   └── app/
│       ├── main.py
│       ├── core/
│       │   ├── security.py          # ⚠️ NÃO tem get_current_user — só JWT utilities
│       │   └── deps.py              # ✅ get_current_user mora AQUI
│       ├── models/
│       ├── schemas/
│       ├── routers/
│       │   ├── portfolios.py        # ✅ PositionItem/SummaryResponse com Optional nullable
│       │   ├── transactions.py      # ✅
│       │   ├── assets.py            # ✅
│       │   ├── dividends.py         # ✅
│       │   ├── prices.py            # ✅
│       │   ├── proventos.py         # ✅
│       │   ├── performance.py       # ✅ AsyncSession
│       │   ├── treasury.py          # ✅
│       │   ├── admin.py             # ✅
│       │   └── [stubs: analysis, fixed_income, goals, irpf, fx]
│       └── services/
│           ├── quotes_service.py       # ✅ ThreadPoolExecutor global + cripto paralelo
│           ├── portfolio_service.py    # ✅ PM ponderado correto + enrich nullable + recalc
│           ├── auth_service.py         # ✅
│           └── [stubs: treasury_service]
│
└── frontend/
    └── src/
        ├── index.css
        ├── components/
        │   ├── ui/
        │   │   └── KpiCard.tsx
        │   └── layout/
        │       ├── AppLayout.tsx
        │       ├── Sidebar.tsx
        │       ├── Topbar.tsx
        │       ├── BottomNav.tsx
        │       ├── AuthLayout.tsx
        │       └── UserMenu.tsx
        ├── pages/
        │   ├── ResumePage.tsx
        │   ├── ProventosPage.tsx
        │   ├── RentabilidadePage.tsx
        │   ├── Transacoes.tsx
        │   ├── PatrimonioPage.tsx
        │   ├── patrimonio/
        │   │   └── TesouroDiretoPage.tsx
        │   ├── Configuracoes.tsx
        │   ├── AdminPanel.tsx
        │   └── [stubs: IRPFPage, AnalisePage, MetasPage]
        ├── hooks/
        │   └── useTreasury.ts
        └── store/
            └── appStore.ts
```

> **⚠️ Armadilha recorrente — import `get_current_user`:**
> `get_current_user` vive em `app.core.deps`, **NÃO** em `app.core.security`.
> Qualquer novo router deve usar `from app.core.deps import get_current_user`.

---

## Status Real dos Módulos

### ✅ Funcionando

| Módulo | Detalhes |
|---|---|
| **Autenticação** | Cadastro, login JWT, refresh token, recuperação de senha |
| **Carteiras (Portfolios)** | CRUD completo, múltiplas carteiras por usuário |
| **Transações** | Compra/venda de todos os tipos de ativo, Preço Médio Ponderado |
| **Tesouro Direto** | Busca autocomplete (BRAPI), campos específicos, salva com ticker slug até 100 chars |
| **Posições** | Agrupadas por classe, PM ponderado, cotação atual (`null` quando indisponível), resultado em `null` quando sem cotação |
| **Cotações** | BRAPI (nacionais); yfinance (STOCK/ETF_INT); BRAPI `/v2/crypto` (cripto BRL) — todas em paralelo |
| **Resumo (Dashboard)** | Patrimônio total, total investido, lucro e variação **usando apenas ativos com cotação**; proventos 12m |
| **Proventos** | Cadastro manual, histórico, consolidação |
| **Eventos Corporativos** | Grupamento, desdobramento, bonificação |
| **Rentabilidade** | Retorno por carteira (absoluto e %) |
| **Admin** | Painel de usuários, edição de role inline |
| **PatrimonioPage** | KPIs, alocação por classe, donut chart, tabela de posições com filtro |
| **KpiCard** | layout: label → valor R$ (grande) → variação % (colorida) → subValue → subLabel |
| **Configurações** | Minha Conta: perfil, avatar, senha, excluir conta |
| **Layout responsivo** | Sidebar drawer mobile 280ms, BottomNav + FAB, hamburger Topbar |
| **Testes automatizados** | ~46 testes pytest; fixtures SQLite async; `make test` |
| **AddTransactionModal global** | Montado no AppLayout; acessível via `openTransactionModal(prefill?)` do store |

### 🚧 Parcialmente Implementado

| Módulo | O que existe | O que falta |
|---|---|---|
| **IRPF** | Model + router stub | Apuração, cálculo DARF, exportação |
| **Análise IA (Gemini)** | Router stub | `analysis_service.py`, prompts, tela |
| **Renda Fixa** | Model + router stub | CRUD backend + tela frontend |
| **Metas (Goals)** | Model criado | CRUD backend + tela |
| **Benchmarks** | Estrutura preparada | Integração CDI/IBOV/IPCA/IFIX |
| **FX (câmbio)** | Router básico | USD/BRL em tempo real |
| **Tesouro Direto — edição** | Cadastro funcional; botão lápis abre modal com prefill | `treasury_service.py` quase vazio; `PUT /treasury/{id}` pendente no backend |
| **Tabelas → Cards mobile** | Layout base pronto | Cards por posição/transação/provento no mobile |
| **Modais bottom sheet** | `TransactionForm` responsivo | Drawer bottom-up mobile |
| **Gráficos responsivos** | Donut chart existente | `ResponsiveContainer` + legendas adaptativas |

### 🔧 Dívidas Técnicas Restantes

| Item | Arquivo(s) | Ação |
|---|---|---|
| JWT em localStorage | `frontend/src/services/api.ts` | Migrar para HttpOnly Cookie antes de SaaS |
| Cache em memória não escala multi-worker | `quotes_service.py` | Migrar para Redis (Sprint 15) |
| Cobertura de testes < 70% | `backend/tests/` | Ampliar nos próximos sprints |

---

## Bugs Corrigidos (histórico)

### Sprint 4 — 15 Jun 2026

| # | Bug / Problema | Causa | Correção |
|---|---|---|---|
| 18 | **`enrich_with_prices`: sem cotação retornava `result_abs = 0.0` e usava `avg_price` como cotação** | `prices.get(ticker) or avg_price` como fallback | `current_price`, `current_value`, `result_abs`, `result_pct` retornam `None` quando cotação ausente |
| 19 | **`recalc_positions`: crash quando `fees=None`** | `fees` sem `or 0.0` | `float(tx.fees or 0.0)` em todas as operações |
| 20 | **Resumo somava ativos sem cotação no `total_current`** | Sem distinção entre ativos com/sem cotação | `total_current` calculado apenas sobre ativos com cotação disponível |
| 21 | **Import morto `from sqlalchemy.orm import Session`** em `portfolio_service.py` | Resíduo de migração Sprint 3 | Removido |

### Sprint 3 — 15 Jun 2026

| # | Bug | Causa | Correção |
|---|---|---|---|
| — | `performance_service.py` / `routers/performance.py` com `Session` síncrona | Resíduo legado | Migrado para `AsyncSession` (commits `297b7e8b`, `07b89607`) |

### Sessão 12 Jun 2026

| # | Bug | Causa | Correção |
|---|---|---|---|
| 14 | Servidor não subia — `dividends.py` | `from app.core.security import get_current_user` | Corrigido para `app.core.deps` |
| 15 | KpiCard: R$ e % na ordem errada | `subLabel/subValue` antes da variação % | Reordenado |
| 16 | TesouroDiretoPage com modal duplicado | Modal próprio além do global no AppLayout | Removido; usa `openTransactionModal` do store |
| 17 | Servidor não subia — `prices.py` | Mesmo erro do #14 | Corrigido |

### Sessão Junho 2026 (1ª parte)

| # | Bug | Causa | Correção |
|---|---|---|---|
| 1 | P. Atual = P. Médio na tabela | `prices.get(ticker) or avg_price` | `current_price = None`; frontend exibe `—` |
| 2 | Tesouro Direto não salvava | `ticker VARCHAR(20)` truncava slugs | `String(100)` + migration 002 |
| 3 | Tesouro Renda+ sumia no autocomplete | Interface sem campo `slug` | Adicionado `slug: string \| null`; debounce 500ms |
| 4 | Cripto com valor errado | `CRIPTO` em `INTL_TYPES` → yfinance USD | Movido para `BR_TYPES`; `_fetch_brapi_crypto()` BRL |
| 5 | Crash `Cannot read .map` | `group.items` vs `group.positions` | Corrigido para `group.positions` |
| 6 | Nome do ativo ausente no autocomplete | Campo `name` ignorado | Corrigido |
| 7 | PatrimonioPage não carregava | `usePositions(0)` com ID inválido | Usa `selectedPortfolioId` do store |
| 8 | Seletor de carteira duplicado | Switcher próprio na página | Removido |
| 9 | Rota Configurações quebrada | Import `require()` dinâmico | Corrigido para import estático |
| 10 | Exclusão de carteira sem feedback | Sem optimistic update | `useDeletePortfolio` com optimistic update |
| 11 | Gráfico de patrimônio histórico vazio | Hook chamava endpoint errado | `usePatrimonioHistory` usa `/equity-history` |
| 12 | Registro com erro de e-mail genérico | `errors.name.message` no campo de e-mail | Corrigido |
| 13 | Prefixo `/api/v1` duplicado | URL hard-coded com prefixo redundante | Removido |

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
| GET | `/portfolios/{id}` | ✅ |
| PUT | `/portfolios/{id}` | ✅ |
| DELETE | `/portfolios/{id}` | ✅ |
| GET | `/portfolios/{id}/summary` | ✅ campos nullable quando sem cotação |
| GET | `/portfolios/{id}/positions` | ✅ campos nullable quando sem cotação |
| GET | `/portfolios/{id}/equity-history` | ✅ |
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

### Tesouro Direto
| Método | Rota | Status |
|---|---|---|
| GET | `/treasury` | ✅ |
| POST | `/treasury` | ✅ |
| DELETE | `/treasury/{id}` | ✅ |
| PUT | `/treasury/{id}` | 🚧 backend pendente |

### Preços
| Método | Rota | Status |
|---|---|---|
| GET | `/prices/{ticker}/history` | ✅ |

### Proventos / Dividendos
| Método | Rota | Status |
|---|---|---|
| GET/POST | `/proventos` | ✅ |
| POST | `/proventos/sync` | ✅ |
| GET/POST | `/dividends` | ✅ |

### Performance
| Método | Rota | Status |
|---|---|---|
| GET | `/performance` | ✅ AsyncSession |
| GET | `/performance/{portfolio_id}` | ✅ AsyncSession |

### Usuário
| Método | Rota | Status |
|---|---|---|
| GET | `/users/me` | ✅ |
| PUT | `/users/me` | ✅ |
| PUT | `/users/me/password` | ✅ |
| PUT | `/users/me/avatar` | ✅ |
| DELETE | `/users/me` | ✅ |

### Stubs (não implementados)
| Rota | Módulo |
|---|---|
| `/analysis/*` | Análise IA Gemini |
| `/irpf/*` | IRPF |
| `/fixed-income/*` | Renda Fixa |
| `/goals/*` | Metas |
| `/fx/*` | Câmbio USD/BRL |
| `/benchmarks/*` | CDI/IBOV/IPCA/IFIX |

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
| `/carteira/patrimonio` | `PatrimonioPage.tsx` | ✅ |
| `/carteira/patrimonio/renda-variavel` | `PatrimonioPage.tsx` | ✅ |
| `/carteira/patrimonio/tesouro` | `TesouroDiretoPage.tsx` | ✅ cadastro / lista / excluir |
| `/carteira/patrimonio/renda-fixa` | `RendaFixaPage.tsx` | 🚧 Stub — próximo sprint |
| `/carteira/configuracoes` | `Configuracoes.tsx` | ✅ perfil + senha |
| `/admin` | `AdminPanel.tsx` | ✅ |
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

# Testes
make test
# ou: docker compose exec backend bash -c "pip install -q -r requirements-test.txt && pytest tests/ -v"
```

---

## Análise de Qualidade do Código

| Área | Nota | Observação |
|---|---|---|
| Arquitetura | 8,5/10 | Sólida, bem separada em camadas |
| Modelagem Financeira | **9/10** | PM ponderado correto; fees de venda isolados; campos nullable sem fallback em PM |
| Qualidade do Código | 8/10 | Clean, delegação adequada |
| Segurança | 7/10 | JWT em localStorage — risco em produção pública |
| Escalabilidade | 7,5/10 | Cache em memória não escala multi-worker |
| **Testabilidade** | **7/10** | ~46 testes pytest; todos critérios de aceite Sprint 4 cobertos; meta 70% cobertura em serviços |
| Responsividade | 6/10 | Layout base responsivo; tabelas/modais mobile pendentes |
| Maturidade Geral | **8,5/10** | Núcleo patrimonial consolidado |

---

## Guia de Continuação

> Use esta seção como ponto de partida em cada nova sessão de desenvolvimento.

---

### Roadmap — 5 Fases

#### ✅ Fase 1 — Fundação (CONCLUÍDA — Junho 2026)

| Item | Status |
|---|---|
| Mover lógica `portfolios.py` → `portfolio_service.py` | ✅ |
| `ThreadPoolExecutor` global para yfinance | ✅ |
| `asyncio.gather()` para cripto paralelo | ✅ |
| Migration Alembic `ticker VARCHAR(100)` | ✅ migration 002 |
| Limpeza de arquivos duplicados frontend | ✅ |
| Suite de testes automatizados | ✅ ~46 testes, `make test` |

---

#### ✅ Fase 2a — Núcleo Patrimonial (CONCLUÍDA — Sprint 4, Jun 2026)

| Item | Status |
|---|---|
| PM ponderado correto (compra, venda, fees) | ✅ |
| Posições zeradas removidas (renda variável + Tesouro) | ✅ |
| `current_price/value/result = null` sem cotação | ✅ |
| Resumo com campos nullable, cálculo só sobre ativos com cotação | ✅ |
| Testes cobrindo todos os critérios de aceite Sprint 4 | ✅ 23 cenários |
| Todos os services/routers com `AsyncSession` exclusivamente | ✅ Sprint 3 |

---

#### 🟡 Fase 2b — Core Financeiro Completo (Em andamento)

| Item | Status | Próximo passo |
|---|---|---|
| **Renda Fixa CRUD** | ⏳ Pendente | `fixed_income_service.py` + `RendaFixaPage.tsx` |
| **Tesouro Direto — edição real backend** | 🚧 Parcial | `PUT /treasury/{id}` funcional no backend |
| **FX USD/BRL** | ⏳ Pendente | `fx_service.py` + exibir BRL na PatrimonioPage |
| **Benchmarks CDI/IBOV/IFIX/IPCA** | ⏳ Pendente | Integração BRAPI + BACEN + gráfico |

---

#### 🟠 Fase 3 — Responsividade Completa (Em andamento)

| Item | Status |
|---|---|
| AppLayout responsivo + Sidebar drawer | ✅ Slide-in 280ms |
| Topbar + FAB + BottomNav | ✅ |
| CSS global responsivo | ✅ |
| Tabelas → Cards mobile | ⏳ |
| Gráficos responsivos | ⏳ |
| Modais bottom sheet | ⏳ |

---

#### 🟡 Fase 4 — Valor Estratégico

| Item | Status |
|---|---|
| Metas financeiras | ⏳ |
| IRPF | ⏳ |
| Exportação CSV | ⏳ |
| Engine de posições materializadas | ⏳ |

---

#### 🟢 Fase 5 — Diferencial Competitivo

| Item | Status |
|---|---|
| Análise IA Gemini | ⏳ |
| Importação CSV corretoras | ⏳ |
| HttpOnly Cookie | ⏳ |
| Cache Redis | ⏳ |

---

### 🚀 Próximos itens na fila (Sprint 5)

```
SPRINT 5 — Cotações e Integrações de Mercado
  ├── Revisão BRAPI: ações, FIIs, ETFs nacionais, cripto e Tesouro
  ├── Revisão yfinance: stocks e ETFs internacionais
  ├── Tratamento claro para falha externa (não derrubar /positions)
  ├── Cache em memória ou Redis
  ├── Logs suficientes para diagnóstico de falha externa
  └── Variáveis de ambiente sem token = fallback claro
```

---

### Contexto técnico importante para próximas sessões

**⚠️ `get_current_user` mora em `app.core.deps`, não em `app.core.security`.**
Qualquer novo router: `from app.core.deps import get_current_user`.

**Regras de PM ponderado (imutáveis):**
- Compra: PM recalculado incluindo `fees`.
- Venda: PM **invariante**; `total_cost -= avg_price * qty_vendida`.
- `fees` de venda **não** entram no PM.
- Posição zerada (`qty <= 1e-9`) é removida.
- Sem cotação → `current_price = None`, nunca `avg_price`.
- Módulo de IRPF **deve** usar este mesmo método.

**Padrão de cotações:** `get_prices()` retorna `dict[str, float]` — tickers ausentes = cotação indisponível. Nunca usar `prices.get(ticker) or avg_price`.

**Padrão de posições:** backend retorna lista flat de `PositionItem`; `toPositionGroups()` em `usePortfolio.ts` agrupa por `asset_type`; campo é `group.positions` (não `.items`).

**Modal global de transações:** `AddTransactionModal` montado no `AppLayout.tsx`. Para abrir: `useAppStore(s => s.openTransactionModal)` com prefill `{ tab, ticker, assetName }`.

**Tesouro Direto:** ticker = slug BRAPI (ex: `TESOURO-SELIC-01032031`); até 100 chars. Edição real (`PUT`) no backend ainda não implementada.

**Cripto:** via BRAPI `/api/v2/crypto?coin={TICKER}&currency=BRL` → BRL direto. `asset_type = CRIPTO` → `_fetch_brapi_crypto()`, nunca yfinance.

**Seleção de carteira:** `selectedPortfolioId` no store Zustand. Se `null`, exibir empty state.

**Sidebar mobile:** `sidebarOpen` no `useAppStore`. Fecha automaticamente ao trocar de rota.

**KpiCard — ordem:** label → valor R$ (2xl bold) → variação % (colorida) → subValue → subLabel.

**Testes:** `make test`. Fixtures em `backend/tests/conftest.py` (SQLite async em memória). Mocks via `unittest.mock.patch`.
