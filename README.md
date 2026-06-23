# SGI v2 — Sistema de Gerenciamento de Investimentos

> Plataforma pessoal para controle e análise de carteira de investimentos.
> Backend FastAPI + PostgreSQL + Redis. Frontend React (em desenvolvimento).

---

## 🚀 Stack

| Camada | Tecnologia |
|---|---|
| Backend | FastAPI 0.115, Python 3.12, SQLAlchemy 2 async |
| Banco de dados | PostgreSQL 16 |
| Cache | Redis 7 |
| Migrations | Alembic |
| Scheduler | APScheduler 3 |
| Autenticação | JWT (access + refresh token rotativo) |
| Dados de mercado | BRAPI Pro + Alpha Vantage + yfinance |
| Containerização | Docker + Docker Compose |
| Frontend | React + TypeScript + Vite (em desenvolvimento) |

---

## ⚡ Setup rápido

### Pré-requisitos
- Docker Desktop instalado e rodando
- Git

### 1. Clone e configure
```bash
git clone https://github.com/lfragoso93-web/sig-v2.git
cd sig-v2
cp backend/.env.example backend/.env
# Edite backend/.env com suas chaves (BRAPI_TOKEN, SECRET_KEY, etc.)
```

### 2. Suba os containers
```bash
docker compose up -d --build
```

### 3. Verifique o health
```bash
curl http://localhost:8000/health
# Esperado: {"status": "ok", "checks": {"postgres": "ok", "redis": "ok"}}
```

### 4. Acesse a documentação interativa
```
http://localhost:8000/docs
```

### 5. Popular catálogo de ativos (primeira vez)
```powershell
# PowerShell — faça login primeiro para obter o token
$login = Invoke-RestMethod -Method Post `
  -Uri "http://localhost:8000/api/v1/auth/login" `
  -ContentType "application/json" `
  -Body '{"email": "admin@sgi.com", "password": "sua_senha"}'
$token = $login.access_token

# Dispara o seed
Invoke-RestMethod -Method Post `
  -Uri "http://localhost:8000/api/v1/admin/assets/seed" `
  -Headers @{ Authorization = "Bearer $token" }
```

---

## 📁 Estrutura do projeto

```
sig-v2/
├── backend/
│   ├── app/
│   │   ├── core/          # config, database, security, scheduler, cache
│   │   ├── integrations/  # brapi, alpha_vantage
│   │   ├── models/        # SQLAlchemy models
│   │   ├── routers/       # FastAPI routers
│   │   ├── schemas/       # Pydantic schemas
│   │   └── services/      # lógica de negócio
│   ├── alembic/           # migrations
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/              # React + TypeScript (em desenvolvimento)
├── docker-compose.yml
├── CHANGELOG.md
└── ROADMAP_SPRINTS.md
```

---

## 🔑 Variáveis de ambiente principais

| Variável | Descrição |
|---|---|
| `SECRET_KEY` | Chave JWT (mínimo 32 chars) |
| `BRAPI_TOKEN` | Token BRAPI Pro |
| `ALPHA_VANTAGE_API_KEY` | Chave Alpha Vantage (opcional) |
| `DATABASE_URL` | URL do PostgreSQL |
| `REDIS_URL` | URL do Redis |
| `SUPERADMIN_EMAIL` | E-mail do superadmin inicial |
| `SUPERADMIN_PASSWORD` | Senha do superadmin inicial |
| `CORS_ORIGINS` | Origens permitidas (separadas por vírgula) |

Veja o arquivo `backend/.env.example` para a lista completa.

---

## 📡 Principais endpoints

### Auth
| Método | Rota | Descrição |
|---|---|---|
| POST | `/api/v1/auth/login` | Login (retorna access + refresh token) |
| POST | `/api/v1/auth/refresh` | Renova access token |
| POST | `/api/v1/auth/logout` | Invalida refresh token |

### Admin (superadmin)
| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/v1/admin/users` | Lista usuários |
| POST | `/api/v1/admin/assets/seed` | Popula catálogo de ativos via BRAPI |
| GET | `/api/v1/admin/stats` | Estatísticas do sistema |

### Portfólios
| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/v1/portfolios/` | Lista carteiras do usuário |
| POST | `/api/v1/portfolios/` | Cria carteira |
| GET | `/api/v1/portfolios/{id}/summary` | Resumo patrimonial |
| GET | `/api/v1/portfolios/{id}/positions` | Posições abertas |
| GET | `/api/v1/portfolios/{id}/patrimonio-history` | Histórico de patrimônio |

### Dados de mercado
| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/v1/quotes/{ticker}` | Cotação atual |
| GET | `/api/v1/prices/{ticker}/history` | Histórico de preços |
| GET | `/api/v1/fx/rate` | Cotação de câmbio |
| GET | `/api/v1/assets` | Catálogo de ativos |

---

## 🕐 Jobs automáticos (Scheduler)

| Job | Frequência | Descrição |
|---|---|---|
| `job_update_prices` | Seg–Sex 18h30 | Atualiza preços de fechamento |
| `job_update_dividends` | Diário 19h | Sincroniza proventos |
| `job_update_fx` | Seg–Sex 18h | Atualiza cotações de câmbio |
| `job_seed_assets` | Segunda 03h | Seed incremental de novos ativos |

---

## 📋 Documentação

- [CHANGELOG.md](./CHANGELOG.md) — histórico de mudanças
- [ROADMAP_SPRINTS.md](./ROADMAP_SPRINTS.md) — sprints planejadas e andamento
- [http://localhost:8000/docs](http://localhost:8000/docs) — Swagger UI (com servidor rodando)
