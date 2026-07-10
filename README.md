# SGI v2 — Sistema de Gestão de Investimentos

Plataforma pessoal para acompanhamento, consolidação e análise de investimentos.
Monorepo com backend FastAPI e frontend React + TypeScript.

A branch padrão de desenvolvimento é `stable-15jun`.

---

## Status atual — 10/07/2026

A entrega atual consolida a camada financeira e corrige fluxos críticos antes da continuidade das próximas sprints.

### Principais entregas

- Serviço canônico de KPIs para Resumo, Patrimônio, Rentabilidade e endpoints de performance.
- Evolução patrimonial diária e mensal com manutenção automática de snapshots e fallback histórico.
- KPIs atuais, resultados realizados, retorno mensal e retorno de 12 meses alinhados.
- Importação CSV autenticada com modelo, preview, `dry_run`, persistência, mensagens em português e invalidação de cache.
- Isolamento de carteiras por usuário, inclusive superadmins.
- Proventos vinculados exclusivamente à carteira selecionada no topbar.
- Seed histórico de proventos idempotente, com complemento histórico e materialização por posição elegível.
- Tratamento de tickers sem histórico e cache temporário de indisponibilidade.
- Tesouro Direto com catálogo canônico e fallback de preços do Tesouro Transparente para RendA+ e Educa+.
- Seletores locais de carteira removidos das páginas Proventos e Rentabilidade.

### Validação local realizada

- Backend e frontend compilando via Docker Compose.
- Login e troca de usuário validados.
- Resumo, Patrimônio e Rentabilidade com KPIs consistentes.
- Gráficos de evolução restaurados.
- Importação CSV validada com linhas válidas e inválidas.
- Sincronização de proventos reexecutável sem violações de unicidade.
- Testes backend focados em portfolio, performance e CSV aprovados.
- Typecheck e build do frontend aprovados.

---

## Próximos focos

1. Finalizar a issue #124: dropdown da tabela do Resumo, variação por classe e acabamento de UX.
2. Robustecer Backup/Restore (#83).
3. Corrigir administração de usuários e perfis (#98).
4. Revisar documentação pública e referências a provedores (#80).
5. Implementar Google OAuth (#97).
6. Avançar em IRPF (#56), Análise de Carteira (#57) e Janela Global do Ativo (#58).

---

## Funcionalidades implementadas

### Resumo e Patrimônio

- KPIs consolidados de patrimônio, investido, resultado, proventos e variação atual.
- Evolução diária e mensal com filtros de período.
- Distribuição por classe e metas de alocação.
- Score HHI, Top 5 posições e desvio da alocação ideal.

### Rentabilidade

- KPIs atuais vindos da fonte financeira canônica.
- Ganho realizado e não realizado.
- Retorno mensal, 12 meses e desde o início.
- Gráfico mensal com benchmarks.
- Distribuição por classe e tabela por ativo.

### Proventos

- Dividendos, JCP, rendimentos, amortizações, bonificações e subscrições.
- Data Com, Data Ex e pagamento separados.
- Materialização por carteira conforme posição elegível.
- Histórico completo por ativo, com seed idempotente.
- Filtros por status, classe, tipo e ano.
- Eventos não-cash fora dos totais financeiros.

### Importação CSV

- Modelo oficial para download.
- Preview antes da importação.
- Validação linha a linha.
- `dry_run` e persistência efetiva.
- Mensagens localizadas e atualização dos caches financeiros.

### Tesouro Direto

- Catálogo canônico de títulos.
- Histórico e preços atuais.
- Suporte a Selic, Prefixado, IPCA+, RendA+ e Educa+.
- Fallback oficial para títulos sem preço no provedor primário.

### Conta e configurações

- Login JWT com refresh token rotativo.
- Recuperação e alteração autenticada de senha.
- Carteiras isoladas por usuário.
- Configuração de metas de alocação.

---

## Stack tecnológica

### Backend

| Tecnologia | Uso |
|---|---|
| Python 3.12 | Linguagem base |
| FastAPI | API async |
| SQLAlchemy async | ORM |
| Alembic | Migrations |
| PostgreSQL | Banco de dados |
| Redis | Cache e locks |
| APScheduler | Jobs agendados |
| JWT | Autenticação |

### Frontend

| Tecnologia | Uso |
|---|---|
| React 19 | Interface |
| TypeScript | Tipagem |
| Vite | Build |
| TailwindCSS 4 | Estilos utilitários |
| Recharts | Gráficos |
| React Query | Estado servidor |
| Zustand | Estado global |
| Axios | Cliente HTTP |

---

## Estrutura do projeto

```text
sig-v2/
├── backend/
├── frontend/
├── docs/
├── docker-compose.yml
├── docker-compose.prod.yml
├── CHANGELOG.md
├── ROADMAP_SPRINTS.md
└── README.md
```

---

## Como rodar

### Docker

```bash
cp .env.example .env
docker compose up -d --build
```

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`

### Desenvolvimento local

```bash
# Backend
cd backend
python -m venv .venv
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

---

## Documentação

| Documento | Conteúdo |
|---|---|
| `CHANGELOG.md` | Histórico de mudanças |
| `ROADMAP_SPRINTS.md` | Entregas e próximas sprints |
| `docs/REVISAO_INTERFACE.md` | Baseline visual e responsivo |
| `SUMARIO_EXECUTIVO.md` | Visão executiva |
| `GAPS_ANALISE_COMPLETA.md` | Gaps identificados |
| `PLANO_ACAO_EXECUTAVEL.md` | Plano de ação |
