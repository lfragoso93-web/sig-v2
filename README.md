# SGI v2 — Sistema de Gestão de Investimentos

Plataforma pessoal para acompanhamento, consolidação e análise de investimentos.
Monorepo com backend FastAPI e frontend React + TypeScript.

A branch padrão de desenvolvimento é `stable-15jun`.

---

## Status atual — 13/07/2026

A entrega atual amplia a integridade histórica da carteira, moderniza a integração com dados de mercado e melhora os fluxos de importação e gerenciamento de carteiras.

### Novidades da versão

- Cliente isolado para a API v2 do provedor principal de mercado.
- Resolução automática de tickers antigos e renomeados.
- Validação temporal de ticker pela data efetiva do renome.
- Persistência de aliases históricos de ativos.
- Fundação do motor de eventos corporativos com suporte inicial a `TICKER_CHANGE`.
- Conversão automática de saldo remanescente para o ticker atual sem alterar transações históricas.
- Reconstrução automática de snapshots diários após importação CSV.
- Recalculo histórico da rentabilidade após lançamentos retroativos.
- Filtros interativos nos cards de linhas válidas, avisos e erros do CSV.
- Edição de nome e descrição de carteiras pelo próprio usuário.
- Correções no fluxo Alembic para ambientes com múltiplas heads válidas.

### Principais entregas consolidadas

- Serviço canônico de KPIs para Resumo, Patrimônio e Rentabilidade.
- Evolução patrimonial diária e mensal com snapshots automáticos.
- Importação CSV autenticada com preview, `dry_run`, persistência e validação integral.
- Isolamento de carteiras por usuário e exclusão segura com auditoria preservada.
- Administração de usuários com proteção do último superadmin.
- Proventos vinculados à carteira selecionada no topbar.
- Tesouro Direto com catálogo canônico e fallback de preços.

---

## Próximos focos

1. Continuar o motor de eventos corporativos e a integração complementar com HG Brasil (#129).
2. Avançar na cobertura por ticker e no enriquecimento de ativos via API v2 (#130).
3. Implementar a primeira fase segura de Backup/Restore (#83).
4. Implementar Google OAuth (#97).
5. Refinar a experiência da página Patrimônio (#90).
6. Evoluir Proventos, Análise de Carteira, Janela Global do Ativo e IRPF (#131, #57, #58 e #56).

---

## Funcionalidades implementadas

### Resumo, Patrimônio e Rentabilidade

- KPIs consolidados de patrimônio, investido, resultado, proventos e variação atual.
- Evolução diária e mensal com filtros de período.
- Distribuição por classe e metas de alocação.
- Variação diária por classe separada da rentabilidade acumulada.
- Ganho realizado e não realizado.
- Retorno mensal, 12 meses e desde o início.
- Snapshots diários reconstruídos automaticamente após importações retroativas.

### Proventos

- Dividendos, JCP, rendimentos, amortizações, bonificações e subscrições.
- Data Com, Data Ex e pagamento separados.
- Materialização por carteira conforme posição elegível.
- Histórico completo por ativo, com seed idempotente.
- Eventos não monetários fora dos totais financeiros.

### Importação CSV

- Modelo oficial, preview, validação linha a linha e `dry_run`.
- Bloqueio enquanto existirem erros, avisos impeditivos ou falhas globais.
- Cards clicáveis para filtrar linhas válidas, avisos e erros.
- Resolução de tickers antigos com validação pela data da operação.
- Rebuild automático de snapshots e invalidação de caches financeiros.

### Eventos corporativos e aliases

- Modelo de aliases históricos de ativos.
- Detecção de renome de ticker via API v2.
- Evento corporativo `TICKER_CHANGE` idempotente por carteira.
- Conversão automática de saldo remanescente para o ticker atual.
- Preservação das compras e vendas históricas originais.
- Preparação para splits, grupamentos, bonificações, incorporações e conversões futuras.

### Conta e administração

- Login JWT com refresh token rotativo.
- Recuperação e alteração autenticada de senha.
- Carteiras isoladas por usuário.
- Criação, edição e exclusão segura de carteiras.
- Administração de usuários com edição de nome, papel e status.
- Proteção contra remoção do último superadmin.

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

## Como rodar

```bash
cp .env.example .env
docker compose up -d --build
```

Para ambientes com múltiplas heads Alembic válidas, o entrypoint aplica `alembic upgrade heads`.

---

## Documentação

| Documento | Conteúdo |
|---|---|
| `CHANGELOG.md` | Histórico de mudanças |
| `ROADMAP_SPRINTS.md` | Entregas e próximas sprints |
| `docs/BRAPI_V2_INVENTORY.md` | Inventário técnico da integração de mercado |
| `docs/CSV_IMPORT_PIPELINE.md` | Fluxo de validação, importação e rebuild de snapshots |
| `docs/CORPORATE_ACTIONS.md` | Fundação do motor de eventos corporativos |
| `docs/REVISAO_INTERFACE.md` | Baseline visual e responsivo |