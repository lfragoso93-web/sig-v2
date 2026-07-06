# SGI v2 — Sistema de Gestão de Investimentos

Plataforma pessoal de acompanhamento e análise de investimentos.
Monorepo com backend FastAPI e frontend React + TypeScript.

A branch padrão de desenvolvimento é `stable-15jun`.

---

## Status atual — 06/07/2026

### Entrega mais recente

A validação pós-pipeline da página **Proventos** foi concluída pela issue #95, dando continuidade à entrega do pipeline completo de mercado e proventos de renda variável nacional da issue #92 / PR #93.

Principais entregas recentes:

- Agregações de proventos revisadas para usar elegibilidade por Data Com, com Data Ex como fallback.
- Eventos não-cash seguem visíveis quando relevantes, mas não inflam totais financeiros.
- Cards/KPIs de Proventos sincronizados com os mesmos filtros da tabela.
- Tabela de Proventos revisada com Data Com, Data Ex, pagamento, quantidade elegível, valores unitários e totais.
- Coluna técnica “Natureza” removida da tabela para simplificar a experiência do usuário.
- Cobertura automatizada adicionada para cash vs. não-cash, elegibilidade por Data Com e agregações.
- Ajustes pontuais de UX em Transações para garantir botões de editar/excluir visíveis e clicáveis.

A revisão visual e responsiva do sistema segue como baseline consolidado pela issue #103 e pelas PRs #104, #105, #106, #107 e #108.

---

## Próximos focos sugeridos

1. Admin: corrigir edição de usuários e alteração de perfil pelo superadmin (#98).
2. Compliance: revisar documentação pública, Swagger/OpenAPI e mensagens para manter provedores descritos de forma genérica (#80).
3. Auth: implementar login com Google OAuth (#97).
4. Performance: mapear queries críticas, índices e possíveis N+1.
5. Importação CSV: preparar fluxo de importação de ativos em lote (#82).

---

## Funcionalidades implementadas

### Dashboard principal

- KPIs consolidados de patrimônio, resultado, proventos e variação atual.
- Evolução patrimonial com filtro de período e classe de ativo.
- Fallback automático quando não existem snapshots.
- Tabela de posições agrupada por classe.
- Layout revisado com cards, filtros e tabelas mais responsivos.

### Rentabilidade

- KPIs de rentabilidade com visão consolidada.
- Gráfico mensal com benchmarks.
- Distribuição por classe em cards.
- Tabela por ativo com filtros e toggle de posições zeradas.
- Blocos reorganizados para melhor leitura.

### Patrimônio

- Visão consolidada com KPIs, evolução mensal e alocação por classe.
- Análise com Score HHI, Top 5 posições, concentração por classe e desvio do alvo.
- Treemap SVG puro.
- Página simplificada para evitar redundância com posições já exibidas no Resumo.

### Proventos

- Histórico de dividendos, JCP, rendimentos, amortizações, bonificações e subscrições por carteira.
- Separação de Data Com, Data Ex e Data de Pagamento.
- Materialização por carteira usando posição elegível na Data Com.
- Filtros por status, classe, tipo de evento e ano.
- Cards com valores líquidos, brutos, últimos 12 meses e média mensal.
- Eventos não-cash mantidos fora dos totais financeiros.
- Paginação e layout fluido.

### Configurações

- Abas de Conta, Carteiras, Distribuição e Avançado.
- Formulários de perfil e senha responsivos.
- Lista de carteiras com ações de renomear e excluir.
- Layout revisado com cards e abas mais confortáveis.

### Telas de entrada

- Login, Registro e Recuperar Senha com padrão visual unificado.
- Card centralizado, largura controlada e mais respiro interno.
- Hierarquia clara entre título, subtítulo, campos e ações.

### Dados e automações

- Asset seed com UPSERT idempotente.
- Pipeline de mercado e proventos para ativos nacionais de renda variável.
- Snapshots patrimoniais com backfill manual/admin e recuperação automática.
- Fallbacks para classes de ativos com provedores de dados externos.
- Scheduler APScheduler.
- Cache Redis.
- Lock distribuído em jobs de sync.

---

## Stack tecnológica

### Backend

| Tecnologia | Uso |
|---|---|
| Python 3.12 | Linguagem base |
| FastAPI | Framework web async |
| SQLAlchemy async | ORM |
| Alembic | Migrations |
| PostgreSQL | Banco de dados |
| Redis | Cache |
| APScheduler | Jobs agendados |
| SlowAPI | Rate limiter global |
| JWT | Auth com refresh token rotativo |

### Frontend

| Tecnologia | Uso |
|---|---|
| React 19 | UI |
| TypeScript | Tipagem |
| Vite | Build tool |
| TailwindCSS 4 | Utilitários CSS |
| Recharts | Gráficos |
| React Query | Cache e estado servidor |
| Zustand | Estado global |
| Lucide React | Ícones |
| Axios | HTTP client |

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

### Com Docker

```bash
cp .env.example .env
docker compose up --build
```

Acesse:

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`

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
| `QUOTES_PROVIDER_TOKEN` | Token do provedor de cotações |
| `SUPERADMIN_EMAIL` | E-mail do superadmin |
| `SUPERADMIN_PASSWORD` | Senha do superadmin |

---

## Documentação complementar

| Documento | Descrição |
|---|---|
| `CHANGELOG.md` | Histórico de mudanças |
| `ROADMAP_SPRINTS.md` | Roadmap de sprints |
| `docs/REVISAO_INTERFACE.md` | Revisão visual, responsividade e baseline definido na #103 |
| `SUMARIO_EXECUTIVO.md` | Visão geral executiva |
| `GAPS_ANALISE_COMPLETA.md` | Análise de gaps |
| `PLANO_ACAO_EXECUTAVEL.md` | Plano de ação |
| `MATRIZ_PRIORIZACAO.md` | Priorização |
