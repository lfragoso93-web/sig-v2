# SIG v2 — Sistema de Gestao de Investimentos

> Sistema pessoal de gestao de carteira de investimentos. Backend FastAPI + Frontend React/Vite + PostgreSQL + Docker.

---

## Stack

| Camada | Tecnologia |
|---|---|
| Backend | Python 3.12, FastAPI 0.137, Uvicorn 0.49, SQLAlchemy 2 (async), Alembic |
| Autenticacao | PyJWT 2.13, bcrypt 5 (nativo — sem passlib) |
| Frontend | React 19, Vite 8, TypeScript 6, Tailwind CSS 4, TanStack Query |
| Banco de dados | PostgreSQL 17 |
| Cache | Redis (opcional) |
| Containerizacao | Docker Compose, Nginx 1.28-alpine |
| CI/CD | GitHub Actions (checkout v6, setup-python v6, setup-node v6) |

---

## Estrutura do Projeto

```
sig-v2/
├── backend/
│   ├── app/
│   │   ├── core/          # config, database, security, deps, asset_types, cache, rate_limiter
│   │   ├── models/        # SQLAlchemy models
│   │   ├── routers/       # FastAPI routers
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── services/      # logica de negocio
│   │   ├── integrations/  # BRAPI, Alpha Vantage, BCB PTAX, yfinance
│   │   ├── migrations/    # scripts SQL versionados
│   │   └── main.py
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── pages/
│   │   ├── services/
│   │   └── stores/
│   ├── package.json
│   ├── package-lock.json
│   └── vite.config.ts
├── docker-compose.yml
├── docker-compose.prod.yml
├── CHANGELOG.md
└── ROADMAP_SPRINTS.md
```

---

## Como rodar localmente

### Pre-requisitos
- Docker Desktop
- Git

### Passos

```bash
# 1. Clone o repositorio
git clone https://github.com/lfragoso93-web/sig-v2.git
cd sig-v2

# 2. Copie e ajuste o .env
cp .env.example .env
# Edite .env com suas variaveis (DATABASE_URL, SECRET_KEY, BRAPI_TOKEN, ALPHA_VANTAGE_API_KEY...)

# 3. Suba os containers
docker compose up -d --build

# 4. Acesse
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000/docs
# Health check: http://localhost:8000/health
```

---

## Variaveis de Ambiente

Veja `.env.example` para a lista completa. As principais:

| Variavel | Descricao |
|---|---|
| `DATABASE_URL` | URL de conexao PostgreSQL async (`postgresql+asyncpg://...`) |
| `SECRET_KEY` | Chave JWT — gere com `openssl rand -hex 32` |
| `BRAPI_TOKEN` | Token da API BRAPI (cotacoes B3, plano Pro) |
| `ALPHA_VANTAGE_API_KEY` | Chave Alpha Vantage — cotacoes e historico de ativos internacionais (NVDA, IVV, INTR, TFLO etc.) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Expiracao do token de acesso (padrao: 30) |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Expiracao do refresh token (padrao: 7) |

---

## Fontes de dados — cotacoes e cambio

### Cotacoes de ativos (quotes_service + price_history_service)

| Tipo de ativo | L1 | L2 | L3 |
|---|---|---|---|
| Acoes BR, FII, ETF, BDR | DB cache | BRAPI (bulk) | yfinance |
| Stocks, ETF INT (USD) | DB cache | Alpha Vantage | yfinance |
| Cripto | DB cache | BRAPI `/v2/crypto` | — |

### Cambio USD/BRL (fx_service)

| Camada | Fonte | Observacao |
|---|---|---|
| L2 (memoria) | `_mem_cache` (TTL 60s) | In-process |
| L1 (banco) | Tabela `fx_rates` | Historico permanente; hoje TTL 900s |
| Primario | BCB PTAX (API oficial) | Sem token, historico desde 1994, definitivo |
| Fallback | AwesomeAPI | Backup se BCB falhar |
| Ultimo recurso | `FALLBACK_RATE = 5.70` | Nunca propaga excecao |

> **Nota:** datas futuras (projecoes do grafico de evolucao patrimonial) sao automaticamente redirecionadas para a cotacao do dia atual, evitando FALLBACK_RATE desnecessario.

---

## Modulos implementados

| Modulo | Status |
|---|---|
| Autenticacao (login, registro, JWT, refresh, logout, blacklist) | ✅ Funcional |
| Gestao de carteiras (CRUD) | ✅ Funcional |
| Transacoes (compra/venda, validacao de saldo, paginacao server-side) | ✅ Funcional |
| Posicoes e patrimonio (preco medio, valor de mercado) | ✅ Funcional |
| Cotacoes BR (BRAPI + yfinance, cache L1/L2/L3 com savepoint) | ✅ Funcional |
| Cotacoes INTL (Alpha Vantage primario + yfinance fallback) | ✅ Funcional — 23 Jun 2026 |
| Cambio USD/BRL (BCB PTAX primario + AwesomeAPI fallback) | ✅ Funcional — 23 Jun 2026 |
| Historico patrimonial (snapshots diarios) | ✅ Funcional |
| Proventos (backfill, listagem, historico, sync manual) | ✅ Funcional |
| Rentabilidade (por ativo, por grupo, total com e sem proventos) | ✅ Funcional — 22 Jun 2026 |
| Metas de alocacao por classe (Distribuicao da Carteira) | ✅ Funcional — 22 Jun 2026 |
| Painel Admin (usuarios, roles, configuracoes em abas) | ✅ Funcional |
| Scheduler (jobs diarios: cotacoes, snapshots) | ✅ Funcional |
| Refresh token blacklist + endpoint /logout | ✅ Funcional — 22 Jun 2026 |
| Audit log + rate limiting (debug.py) | ✅ Funcional — 22 Jun 2026 |
| IRPF (backend + frontend basico) | ✅ Implementado (revisao na Sprint 12) |
| Exibicao de ativos USD com simbolo correto (Stocks/ETF INT) | ✅ Corrigido — 22 Jun 2026 |
| Modal de lancamento — todas as classes de ativo visiveis | ✅ Corrigido — 22 Jun 2026 |
| Historico patrimonial (frontend — graficos) | 🔜 Sprint 8 |
| Renda Fixa e Tesouro Direto (frontend completo) | ⏳ Sprint 10 |
| IRPF (revisao e testes completos) | ⏳ Sprint 12 |

---

## Fluxo de Desenvolvimento

Todo desenvolvimento novo acontece na branch `stable-15jun`. A `main` e a branch de producao e so recebe codigo via Pull Request com CI verde.

### Regra geral

```
stable-15jun  ──●──●──●──●──── PR ──▶  main
                feat  fix  fix        (CI verde)
                                           │
                ◀──── pull origin main ────┘
```

### 1. Antes de comecar qualquer tarefa

Sempre sincronize a branch local com o remoto:

```bash
git checkout stable-15jun
git pull origin stable-15jun
```

### 2. Durante o desenvolvimento

Commits pequenos e descritivos seguindo Conventional Commits:

```
feat(scope): descricao curta
fix(scope): descricao curta
chore(scope): descricao curta
```

### 3. Antes de abrir o PR

Rode localmente para garantir que o CI vai passar:

```bash
# Frontend
cd frontend
npm run typecheck   # zero erros TS
npm run lint        # zero warnings ESLint

# Backend
cd backend
flake8 app/         # zero erros F401/F821
```

### 4. Abrir o Pull Request

PR sempre de `stable-15jun` → `main`. Titulo e descricao devem resumir os commits do ciclo.

### 5. Apos o merge — sincronizar a stable-15jun

```bash
git checkout stable-15jun
git pull origin main
git push origin stable-15jun
```

### Regras de ouro

- **Nunca commitar direto na `main`** — tudo passa por PR
- **CI deve estar verde** antes de solicitar merge (typecheck + lint)
- **Commits atomicos** — um problema/feature por commit, facilita rollback
- **Sincronize a `stable-15jun` imediatamente apos cada merge** para evitar divergencias acumuladas

---

## Convencoes de layout responsivo

O projeto **nao depende de classes Tailwind com breakpoints** (`md:hidden`, `hidden md:block`) para alternar layouts. Todo comportamento responsivo e implementado via hook `useIsDesktop()` (`window.matchMedia`) com renderizacao condicional React. Isso garante que mobile e desktop nunca sejam renderizados simultaneamente.

```tsx
// padrao correto
const isDesktop = useIsDesktop()   // hook com MediaQueryList
return isDesktop ? <Tabela /> : <Cards />
```

---

## Convencao de campos opcionais de cotacao

Quando o servico de cotacoes nao retorna preco para um ativo, os campos abaixo chegam como `null` tanto no backend quanto no frontend:

| Campo | Tipo | Significado quando null |
|---|---|---|
| `current_price` | `float \| null` | Cotacao indisponivel |
| `current_value` | `float \| null` | Valor de mercado indisponivel |

O frontend exibe `—` nesses casos. **Nunca** repete o `invested_value` no lugar do `current_value`.

---

## Convencao de moeda — ativos internacionais

Ativos com `currency = "USD"` (STOCK, ETF_INTERNACIONAL) exibem preco e valores unitarios em USD com simbolo correto (`$`). Os totais do grupo (Investido / Atual) sao exibidos em BRL, pois o backend ja converte via `fx_rate`.

```ts
// padrao correto
fmtMoney(value, position.currency)   // USD → formatUSD, BRL → formatBRL
formatBRL(group.total_invested)       // total do grupo sempre em BRL
```

---

## Seguranca — Nota importante

O arquivo `reset_pwd.py` foi removido do repositorio em 15/06/2026 pois continha uma senha em texto claro. O arquivo ainda existe no historico do git (commit `8d7a99a9`). Caso o repositorio seja publico, recomenda-se:

```bash
# Remover do historico com git filter-repo
pip install git-filter-repo
git filter-repo --path reset_pwd.py --invert-paths
git push origin main --force
```

> ⚠️ Apos o force push todos os colaboradores devem refazer o clone.

---

## Progresso das Sprints

Veja [ROADMAP_SPRINTS.md](./ROADMAP_SPRINTS.md) para o roadmap completo e [CHANGELOG.md](./CHANGELOG.md) para o historico detalhado de alteracoes.

| Sprint | Status |
|---|---|
| Sprint 0 a 6 + Manutencao | ✅ Concluidas |
| Hotfix 18 Jun — Tabela de ativos | ✅ Concluido |
| Security Hotfix 21 Jun — pydantic-settings CVE | ✅ Concluido |
| Sprint 7 — Rentabilidade | ✅ Concluida — 22 Jun 2026 |
| Sprint 11 — Metas e Alocacao | ✅ Concluida — 22 Jun 2026 |
| Hotfix 23 Jun — BCB PTAX + Alpha Vantage INTL | ✅ Concluido — 23 Jun 2026 |
| Sprint 7.5 — Hardening de Seguranca (C1–C3, A1–A4) | 🔜 Proxima |
| Sprint 8 — Historico Patrimonial (frontend) | ⏳ Planejada |
| Sprints 9 a 15 | ⏳ Planejadas |

---

## Convencoes de commit

Seguimos [Conventional Commits](https://www.conventionalcommits.org/pt-BR/):

```
feat(scope): descricao
fix(scope): descricao
build(deps): upgrade ...
docs: descricao
refactor(scope): descricao
test(scope): descricao
```
