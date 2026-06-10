# SIG v2 — Sistema de Investimentos Gerenciado

> Plataforma full-stack containerizada para gestão de carteiras de investimentos, com suporte a múltiplas carteiras, integração automática de cotações, análise de rentabilidade, proventos, eventos corporativos e módulo de IRPF.

---

## Índice

- [Visão Geral](#visão-geral)
- [Stack Tecnológico](#stack-tecnológico)
- [Arquitetura](#arquitetura)
- [Início Rápido](#início-rápido)
- [Desenvolvimento Local](#desenvolvimento-local)
- [Variáveis de Ambiente](#variáveis-de-ambiente)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Módulos e Funcionalidades](#módulos-e-funcionalidades)
- [Modelos de Dados](#modelos-de-dados)
- [API — Endpoints](#api--endpoints)
- [Scheduler de Cotações](#scheduler-de-cotações)
- [Tipos de Ativos Suportados](#tipos-de-ativos-suportados)
- [Frontend — Páginas e Rotas](#frontend--páginas-e-rotas)
- [Autenticação e Segurança](#autenticação-e-segurança)
- [Docker e Infra](#docker-e-infra)
- [Pendências e Roadmap](#pendências-e-roadmap)

---

## Visão Geral

O **SIG v2** é uma reescrita completa do sistema SIG, projetada para suportar múltiplas carteiras por usuário, integração com IA (Google Gemini), cotações automáticas via BRAPI e Yahoo Finance, gestão de proventos, eventos corporativos (grupamentos, bonificações, desdobramentos) e geração de dados para IRPF.

O sistema é composto por:
- **Backend**: API REST em FastAPI (Python 3.12) com banco PostgreSQL e cache Redis
- **Frontend**: SPA em React 18 + Vite + TypeScript + Tailwind CSS
- **Infra**: Docker Compose para desenvolvimento e produção

---

## Stack Tecnológico

| Camada | Tecnologia | Versão |
|---|---|---|
| Frontend | React + Vite + TypeScript | React 18, Vite 5 |
| Estilo | Tailwind CSS | v3 |
| Estado global | Zustand | - |
| Roteamento | React Router DOM | v6 |
| HTTP Client | Axios | - |
| Backend | FastAPI (Python) | Python 3.12 |
| ORM | SQLAlchemy + Alembic | - |
| Banco de dados | PostgreSQL | v16 |
| Cache | Redis | v7 |
| Cotações nacionais | BRAPI | - |
| Cotações internacionais | yfinance (Yahoo Finance) | - |
| Integração IA | Google Gemini API | - |
| Infra | Docker + Docker Compose | - |
| Web server | Nginx | - |

---

## Arquitetura

```
Browser
  └─> Nginx (porta 80/443)
        ├─> / ──────────────────> Frontend (React SPA)
        └─> /api/* ─────────────> FastAPI Backend
                                      ├─> PostgreSQL (dados persistentes)
                                      ├─> Redis (cache de cotações)
                                      ├─> BRAPI (ações, FIIs, ETFs nacionais)
                                      └─> Yahoo Finance (ações/ETFs internacionais, cripto)
```

### Fluxo de Cotações

```
Scheduler (APScheduler)
  └─> Seg-Sex, 9h-18h, a cada 15 min (horário de Brasília)
        └─> quote_service.py
              ├─> BRAPI → ativos nacionais
              └─> yfinance → ativos internacionais/cripto
                    └─> asset_price (DB) + Redis cache
```

---

## Início Rápido

```bash
# 1. Clone o repositório
git clone https://github.com/lfragoso93-web/sig-v2
cd sig-v2

# 2. Configure as variáveis de ambiente
cp .env.example .env
# Edite .env com sua senha do banco, chave JWT e token BRAPI

# 3. Suba todos os containers
docker compose up -d --build

# 4. Acesse
# Frontend:  http://localhost
# API Docs:  http://localhost/api/v1/docs
# Admin API: http://localhost/api/v1/admin/...
```

---

## Desenvolvimento Local

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Linux/macOS
# .venv\Scripts\activate           # Windows

pip install -r requirements.txt

# Rode o banco via Docker separadamente, ou use um PostgreSQL local
uvicorn app.main:app --reload --port 8000
# Swagger em: http://localhost:8000/docs
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# Acesse: http://localhost:5173
```

### Comandos utilitários (Makefile)

```bash
make up          # docker compose up -d --build
make down        # docker compose down
make logs        # docker compose logs -f
make restart     # down + up
make migrate     # alembic upgrade head (dentro do container)
```

---

## Variáveis de Ambiente

Copie `.env.example` para `.env` e ajuste os valores:

| Variável | Descrição | Obrigatória |
|---|---|---|
| `POSTGRES_DB` | Nome do banco | Sim |
| `POSTGRES_USER` | Usuário do banco | Sim |
| `POSTGRES_PASSWORD` | Senha do banco | Sim |
| `SECRET_KEY` | Chave secreta para JWT | Sim |
| `BRAPI_TOKEN` | Token BRAPI para cotações nacionais | Não (limite menor sem token) |
| `GEMINI_API_KEY` | Chave Google Gemini para IA | Não |
| `APP_PORT` | Porta de acesso (padrão: 80) | Não |
| `ALLOWED_ORIGINS` | Origens CORS permitidas | Não |

---

## Estrutura do Projeto

```
sig-v2/
├── .env.example
├── .gitignore
├── docker-compose.yml
├── docker-compose.prod.yml
├── Makefile
├── README.md
│
├── backend/
│   ├── Dockerfile
│   ├── entrypoint.sh
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/              # Migrations automáticas
│   └── app/
│       ├── main.py           # Ponto de entrada FastAPI
│       ├── scheduler.py      # APScheduler — cotações automáticas
│       ├── core/             # Config, DB, segurança, dependências
│       ├── models/           # SQLAlchemy models (ORM)
│       ├── schemas/          # Pydantic schemas (validação)
│       ├── routers/          # Endpoints da API
│       ├── services/         # Lógica de negócio
│       ├── integrations/     # Integrações externas (BRAPI, yfinance)
│       └── migrations/       # Scripts de migração auxiliares
│
└── frontend/
    ├── Dockerfile
    ├── Dockerfile.prod
    ├── nginx.conf
    ├── vite.config.ts
    ├── tailwind.config.ts
    ├── tsconfig.json
    ├── package.json
    └── src/
        ├── App.tsx           # Root component + providers
        ├── main.tsx          # Entry point
        ├── components/       # Componentes reutilizáveis
        ├── pages/            # Páginas da aplicação
        ├── layouts/          # Layouts (AuthLayout, AppLayout)
        ├── router/           # Definição de rotas React Router
        ├── contexts/         # React Contexts (Auth, Portfolio)
        ├── hooks/            # Custom hooks
        ├── services/         # Chamadas à API (axios)
        ├── store/            # Zustand stores
        ├── lib/              # Utilitários e helpers
        ├── utils/            # Funções utilitárias
        └── styles/           # Estilos globais
```

---

## Módulos e Funcionalidades

### ✅ Implementados

#### Autenticação
- Cadastro de usuários (`POST /auth/register`)
- Login com JWT (`POST /auth/login`)
- Refresh de token
- Recuperação de senha (fluxo front + back)
- Perfil de usuário

#### Carteiras (Portfolios)
- Criação, edição e exclusão de múltiplas carteiras por usuário
- Visualização de carteiras com totais consolidados
- Carteira padrão configurável

#### Ativos
- Cadastro de ativos com tipo, ticker e moeda
- Busca de ativos por ticker (integração BRAPI/yfinance)
- Suporte a: Ação Nacional, FII, ETF Nacional, Ação Internacional, ETF Internacional, Criptomoeda, Renda Fixa, Tesouro Direto

#### Transações
- Lançamento de compras e vendas
- Cálculo automático de preço médio (FIFO)
- Histórico de transações por carteira
- Filtros por ativo, tipo e período

#### Posições
- Cálculo automático de posições consolidadas por carteira
- Exibição de quantidade, preço médio, preço atual, valor total, variação (%)
- Atualização on-demand via `?refresh=true`

#### Cotações
- Atualização automática via scheduler (Seg-Sex, 9h-18h, a cada 15 min)
- Cache Redis para reduzir chamadas às APIs externas
- Suporte a ativos nacionais (BRAPI) e internacionais (yfinance)

#### Proventos
- Registro manual de proventos (dividendos, JCP, rendimentos)
- Sincronização automática via BRAPI para ativos nacionais
- Histórico de proventos por carteira e por ativo
- Consolidação mensal e anual

#### Eventos Corporativos
- Suporte a grupamentos, desdobramentos e bonificações
- Ajuste automático de posições e preço médio ao registrar evento

#### Rentabilidade
- Cálculo de retorno por ativo e por carteira
- Comparativo com benchmarks (CDI, IBOV, IPCA — estrutura preparada)
- Retorno total (absoluto e percentual)

#### Resumo / Dashboard
- Visão consolidada do patrimônio total
- Alocação por tipo de ativo (gráfico de distribuição)
- Proventos do mês
- Variação do dia

#### Configurações
- Configurações de usuário (nome, senha)
- Preferências do sistema (moeda base, benchmark padrão)

#### Admin
- Painel administrativo (acesso restrito a admins)
- Gestão de usuários
- Monitoramento de cotações e scheduler

### 🚧 Parcialmente Implementados (Estrutura Criada, Lógica Pendente)

| Módulo | Status | O que falta |
|---|---|---|
| **IRPF** | Estrutura criada (model + router stub) | Service completo, cálculo de DARFs, exportação |
| **Análise IA (Gemini)** | Router stub criado | Service de análise com Gemini, prompts, respostas |
| **Renda Fixa** | Model + router stub | CRUD completo, cálculo de rendimento |
| **Tesouro Direto** | Model + router stub | CRUD completo, integração com cotações |
| **Metas (Goals)** | Model criado | CRUD frontend, acompanhamento de progresso |
| **Patrimônio** | Página criada (stub) | Integração com posições totais consolidadas |
| **Cotações (quotes router)** | Router stub | Endpoint público de busca de cotações por ticker |
| **FX (câmbio)** | Router básico | Integração completa com taxa de câmbio em tempo real |

---

## Modelos de Dados

### Entidades principais

| Model | Arquivo | Descrição |
|---|---|---|
| `User` | `user.py` | Usuário do sistema |
| `Portfolio` | `portfolio.py` | Carteira de investimentos |
| `Asset` | `asset.py` | Ativo (ação, FII, cripto etc.) |
| `AssetPrice` | `asset_price.py` | Histórico de preços |
| `Transaction` | `transaction.py` | Transações de compra/venda |
| `Position` | `position.py` | Posição consolidada (global) |
| `PortfolioPosition` | `portfolio_position.py` | Posição por carteira |
| `Dividend` | `dividend.py` | Proventos recebidos |
| `CorporateEvent` | `corporate_event.py` | Eventos corporativos |
| `FixedIncome` | `fixed_income.py` | Ativos de renda fixa |
| `Treasury` | `treasury.py` | Títulos do Tesouro Direto |
| `Goal` | `goal.py` | Metas financeiras |
| `IRPF` | `irpf.py` | Dados para declaração de IR |
| `SystemConfig` | `system_config.py` | Configurações do sistema |

---

## API — Endpoints

Base URL: `http://localhost/api/v1`

### Autenticação
| Método | Rota | Descrição |
|---|---|---|
| POST | `/auth/register` | Cadastro de usuário |
| POST | `/auth/login` | Login (retorna JWT) |
| POST | `/auth/refresh` | Renovar token |
| POST | `/auth/forgot-password` | Solicitar reset de senha |
| POST | `/auth/reset-password` | Redefinir senha |

### Usuários
| Método | Rota | Descrição |
|---|---|---|
| GET | `/users/me` | Perfil do usuário logado |
| PUT | `/users/me` | Atualizar perfil |

### Carteiras
| Método | Rota | Descrição |
|---|---|---|
| GET | `/portfolios` | Listar carteiras do usuário |
| POST | `/portfolios` | Criar carteira |
| PUT | `/portfolios/{id}` | Editar carteira |
| DELETE | `/portfolios/{id}` | Excluir carteira |

### Ativos
| Método | Rota | Descrição |
|---|---|---|
| GET | `/assets` | Listar ativos cadastrados |
| POST | `/assets` | Cadastrar ativo |
| GET | `/assets/{id}` | Detalhe do ativo |
| DELETE | `/assets/{id}` | Remover ativo |

### Transações
| Método | Rota | Descrição |
|---|---|---|
| GET | `/transactions` | Listar transações |
| POST | `/transactions` | Registrar transação |
| PUT | `/transactions/{id}` | Editar transação |
| DELETE | `/transactions/{id}` | Excluir transação |

### Posições
| Método | Rota | Descrição |
|---|---|---|
| GET | `/positions` | Posições consolidadas |
| GET | `/positions?refresh=true` | Forçar atualização de cotações |

### Proventos
| Método | Rota | Descrição |
|---|---|---|
| GET | `/proventos` | Listar proventos |
| POST | `/proventos` | Registrar provento manual |
| POST | `/proventos/sync` | Sincronizar via BRAPI |

### Dividendos
| Método | Rota | Descrição |
|---|---|---|
| GET | `/dividends` | Listar dividendos |
| POST | `/dividends` | Registrar dividendo |

### Rentabilidade
| Método | Rota | Descrição |
|---|---|---|
| GET | `/performance` | Rentabilidade consolidada |
| GET | `/performance/{portfolio_id}` | Rentabilidade por carteira |

### Sync
| Método | Rota | Descrição |
|---|---|---|
| POST | `/sync/quotes` | Disparar atualização manual de cotações |

### Admin
| Método | Rota | Descrição |
|---|---|---|
| GET | `/admin/users` | Listar usuários (admin) |
| PUT | `/admin/users/{id}` | Gerenciar usuário (admin) |
| GET | `/admin/config` | Configurações do sistema |

### 🚧 Endpoints Stub (Não implementados)
| Rota | Módulo pendente |
|---|---|
| `/analysis/*` | Análise com IA Gemini |
| `/irpf/*` | IRPF completo |
| `/fixed-income/*` | Renda fixa |
| `/treasury/*` | Tesouro Direto |
| `/goals/*` | Metas |
| `/quotes/{ticker}` | Cotação pontual |

---

## Scheduler de Cotações

Implementado em `backend/app/scheduler.py` usando **APScheduler**:

- **Frequência**: a cada 15 minutos, Seg-Sex, 9h-18h (horário de Brasília)
- **Processo**: busca todos os ativos cadastrados → consulta BRAPI (nacionais) ou yfinance (internacionais/cripto) → salva em `asset_price` → atualiza cache Redis
- **On-demand**: qualquer endpoint de posições aceita `?refresh=true` para forçar atualização imediata

---

## Tipos de Ativos Suportados

| Tipo | Fonte de Cotação | Moeda |
|---|---|---|
| Ação Nacional | BRAPI | BRL |
| FII | BRAPI | BRL |
| ETF Nacional | BRAPI | BRL |
| Tesouro Direto | BRAPI | BRL |
| Ação Internacional (Stock) | Yahoo Finance (yfinance) | USD |
| ETF Internacional | Yahoo Finance (yfinance) | USD |
| Criptomoeda | Yahoo Finance (ticker + `-USD`) | USD |
| Renda Fixa | Manual (sem cotação automática) | BRL |

---

## Frontend — Páginas e Rotas

| Rota | Componente | Status |
|---|---|---|
| `/` | `Landing.tsx` | ✅ Implementado |
| `/login` | `Login.tsx` | ✅ Implementado |
| `/register` | `Register.tsx` | ✅ Implementado |
| `/esqueceu-senha` | `EsqueceuSenha.tsx` | ✅ Implementado |
| `/app/resumo` | `ResumePage.tsx` | ✅ Implementado |
| `/app/lancamentos` | `LancamentosPage.tsx` | ✅ Implementado |
| `/app/transacoes` | `TransacoesPage.tsx` | ✅ Implementado |
| `/app/proventos` | `ProventosPage.tsx` | ✅ Implementado |
| `/app/rentabilidade` | `RentabilidadePage.tsx` | ✅ Implementado |
| `/app/configuracoes` | `Configuracoes.tsx` | ✅ Implementado |
| `/app/patrimonio` | `PatrimonioPage.tsx` | 🚧 Stub |
| `/app/irpf` | `IRPFPage.tsx` | 🚧 Stub |
| `/app/analise` | `AnalisePage.tsx` | 🚧 Stub |
| `/app/metas` | `MetasPage.tsx` | 🚧 Stub |

---

## Autenticação e Segurança

- **JWT (JSON Web Tokens)**: autenticação stateless, tokens com expiração configurável
- **Bcrypt**: hash de senhas
- **Refresh Token**: renovação automática via interceptor Axios no frontend
- **CORS**: configurado via variável `ALLOWED_ORIGINS`
- **Isolamento de dados**: todos os endpoints de dados filtram por `user_id` do token
- **Admin routes**: protegidas por verificação de role `is_superuser`

---

## Docker e Infra

### Desenvolvimento

```bash
docker compose up -d --build
```

Serviços:
- `frontend` — React Dev Server (porta 5173, acessível via nginx)
- `backend` — FastAPI com hot-reload (porta 8000)
- `postgres` — PostgreSQL 16
- `redis` — Redis 7
- `nginx` — Proxy reverso (porta 80)

### Produção

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Diferenciais do ambiente de produção:
- Frontend buildado com `npm run build` e servido pelo Nginx
- Backend sem `--reload`
- Variáveis de ambiente via secrets ou arquivo `.env` externo

### Migrations

O backend executa `alembic upgrade head` automaticamente no `entrypoint.sh` ao subir.

Para criar nova migration manualmente:
```bash
docker compose exec backend alembic revision --autogenerate -m "descricao"
docker compose exec backend alembic upgrade head
```

---

## Pendências e Roadmap

### 🔴 Alta Prioridade

- [ ] **IRPF Service**: implementar lógica completa de cálculo de DARFs, apuração mensal de ganho de capital, exportação de relatório
- [ ] **Renda Fixa CRUD**: telas de cadastro, edição e acompanhamento de ativos de renda fixa no frontend e service no backend
- [ ] **Tesouro Direto CRUD**: idem para Tesouro Direto
- [ ] **PatrimonioPage**: conectar à API de posições consolidadas totais (atualmente é stub)

### 🟡 Média Prioridade

- [ ] **Análise IA (Gemini)**: implementar `analysis_service.py` com integração Google Gemini, prompts de análise de carteira, e conectar ao `AnalisePage.tsx`
- [ ] **Metas (Goals)**: implementar CRUD completo de metas financeiras no frontend e conectar ao `goals_service.py`
- [ ] **Benchmarks de Rentabilidade**: integrar CDI, IBOV e IPCA para comparativo na tela de Rentabilidade
- [ ] **Cotações endpoint público** (`/quotes/{ticker}`): completar `quotes.py` router para busca pontual de cotação

### 🟢 Baixa Prioridade / Melhorias

- [ ] **Testes automatizados**: implementar testes unitários (pytest) no backend e testes de integração
- [ ] **Notificações**: alertas de proventos, variações significativas de ativos
- [ ] **Exportação de dados**: CSV/Excel de transações, proventos e posições
- [ ] **2FA (Two-Factor Auth)**: autenticação em dois fatores
- [ ] **Dark mode**: suporte a tema escuro no frontend
- [ ] **PWA**: configurar Progressive Web App para uso mobile
- [ ] **CI/CD**: pipeline de deploy automático (GitHub Actions)
- [ ] **Limpeza de arquivos duplicados**: existem pares de arquivos legados (ex: `Proventos.tsx` vs `ProventosPage.tsx`, `Transacoes.tsx` vs `TransacoesPage.tsx`, `Rentabilidade.tsx` vs `RentabilidadePage.tsx`, `Resumo.tsx` vs `ResumePage.tsx`) — consolidar em arquivos únicos
- [ ] **FX (câmbio)**: completar integração com taxa USD/BRL em tempo real para cálculo correto de ativos internacionais no total do patrimônio
- [ ] **treasury_service.py**: arquivo quase vazio (71 bytes), implementar lógica de serviço
