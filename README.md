# SIG v2 — Sistema de Gerenciamento de Investimentos

> Plataforma multi-usuário para gestão completa de carteiras de investimentos com IA.

## 🚀 Como rodar

```bash
# 1. Clone o repositório
git clone https://github.com/lfragoso93-web/sig-v2.git
cd sig-v2

# 2. Configure as variáveis de ambiente
cp .env.example .env
# Edite .env com suas chaves (BRAPI, Gemini, etc.)

# 3. Suba tudo com Docker
docker compose up -d

# 4. Acesse
# Frontend: http://localhost:5173
# Backend (API docs): http://localhost:8000/docs
```

## 🧱 Stack

| Camada | Tecnologia |
|--------|------------|
| Backend | FastAPI (Python 3.12) |
| Banco de dados | PostgreSQL 16 |
| Cache | Redis 7 |
| Scheduler | APScheduler |
| IA | Google Gemini 1.5 Pro |
| Frontend | React 18 + Vite + TailwindCSS |
| Infra | Docker Compose |

## 📦 Módulos

- **Carteiras** — múltiplas carteiras por usuário, N ativos por carteira
- **Transações** — compra/venda com preço médio automático
- **Cotações** — integração BRAPI (ações, FIIs, ETFs, Tesouro Direto, cripto, câmbio)
- **Renda Fixa** — cálculo de rentabilidade CDI%, IPCA+, SELIC, prefixado
- **IRPF** — apuração mensal, isenção de ações, compensação de prejuízos
- **Proventos** — dividendos, JCP, rendimentos e projeções
- **Metas** — patrimônio alvo, alocação por classe, DY alvo
- **Análise com IA** — Gemini analisa carteira, lê relatórios PDF, gera sinais

## 🗺️ Roadmap de desenvolvimento

- [x] Bloco 1 — Estrutura base, Docker, configurações
- [ ] Bloco 2 — Models do banco (PostgreSQL + Alembic)
- [ ] Bloco 3 — Autenticação JWT
- [ ] Bloco 4 — Carteiras e transações
- [ ] Bloco 5 — Integração BRAPI (cotações, tesouro, cripto, câmbio)
- [ ] Bloco 6 — Motor de cálculo (preço médio, rentabilidade, renda fixa)
- [ ] Bloco 7 — Módulo IRPF
- [ ] Bloco 8 — Proventos
- [ ] Bloco 9 — Metas
- [ ] Bloco 10 — Análise com IA (Gemini)
- [ ] Bloco 11 — Frontend React

## 📋 Tipos de ativo suportados

`Ação Nacional` · `FII` · `ETF Nacional` · `Tesouro Direto` · `Stock (EUA)` · `ETF Internacional` · `Criptomoeda` · `Renda Fixa`
