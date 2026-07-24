# SGI v2 — Sistema de Gestão de Investimentos

Plataforma pessoal para acompanhamento, consolidação e análise de investimentos, com backend FastAPI e frontend React + TypeScript.

A branch padrão de desenvolvimento é `stable-15jun`. A promoção para `main` ocorre por PR após validação e atualização da documentação viva.

## Status atual — 24/07/2026

O SGI v2 opera com arquitetura **DB-first**: catálogo, preços, taxas, proventos e snapshots são persistidos antes de alimentar KPIs, páginas e gráficos.

A PR #198 foi promovida para a `main` e a Issue #196 foi encerrada após ensaio integral da limpeza em PostgreSQL descartável, com cenário de sucesso e rollback reconciliados. A `stable-15jun` foi sincronizada com a `main` no merge `77783e46042bd32622500705cb7d365f70c728ae`.

A limpeza da base pré-produção real permanece proibida. O próximo gate da Issue #158 é uma autorização operacional separada, com novo backup, nova exportação, novo plano e janela controlada.

### Entregas consolidadas

- Valuation canônico por classe de ativo.
- Contratos `summary.v2` e `rentabilidade.v2` validados em runtime.
- Snapshots patrimoniais diários, mensais e por classe suportada.
- Histórico oficial da B3 via COTAHIST.
- Tesouro Direto com catálogo canônico, ano comercial de RendA+/Educa+ e preços oficiais persistidos.
- Renda Fixa valorizada por motor dedicado.
- CDI e IPCA servidos a partir de séries persistidas.
- Proventos monetários líquidos agregados por data de pagamento.
- Reconciliação entre Resumo, Patrimônio, Rentabilidade e snapshots.
- Cobertura parcial e retornos estimados explicitados no contrato.
- Página Resumo concluída e promovida pela PR #164.
- Fase 2 de Proventos concluída e promovida pela PR #166.
- Fase 3 de Patrimônio concluída e promovida pela PR #184.
- Inventário `pre-prod-inventory.v2` validado no PostgreSQL real: 24 tabelas, 11 preservadas, 3 exportáveis e 10 reconstruíveis.
- Backup `pre-prod-backup.v3` e restauração isolada reconciliados pela Issue #183.
- Dry-run `pre-prod-cleanup-impact.v2` aprovado sem bloqueios, ciclos ou escritas pela Issue #185.
- Exportação `pre-prod-export.v1` validada e promovida pela PR #191.
- Plano `pre-prod-cleanup-execution.v1` validado sem acesso ao banco pela Issue #195 e PR #194.
- Executor e CLI `pre_prod_isolated_cleanup` promovidos pela PR #198.
- Evidências automáticas: `preserved-before.json`, `preserved-after.json`, `post-cleanup-inventory.json`, `reconciliation.json` e `cleanup/execution.json`.
- Ensaio de sucesso `20260723-213000`: 4.673.054 linhas planejadas removidas, tabelas preservadas inalteradas e `reconciliation.ok=true`.
- Ensaio de rollback `20260723-213001`: exit code `22`, nenhuma escrita persistida e `reconciliation.ok=true`.
- Bancos descartáveis do ensaio removidos após a validação.
- Migração Pydantic v2 concluída pela Issue #186.

## Arquitetura resumida

```text
Importação CSV / lançamentos manuais
        ↓
Transações
        ↓
Catálogo canônico de ativos
        ↓
B3 COTAHIST | dados oficiais do Tesouro | séries macroeconômicas | motores dedicados
        ↓
asset_prices / rate_history / proventos
        ↓
Valuation canônico por classe
        ↓
PortfolioSnapshot + PortfolioClassSnapshot
        ↓
summary.v2 / rentabilidade.v2 / posições canônicas
        ↓
Resumo, Patrimônio, Rentabilidade e demais módulos
```

Princípios: DB-first, fonte oficial primeiro, idempotência, ausência não convertida em zero, separação entre valuation intradiário e performance fechada e contratos financeiros únicos.

## Comandos operacionais

```bash
python -m app.cli.pre_prod_inventory
python -m app.cli.pre_prod_backup
python -m app.cli.pre_prod_restore
python -m app.cli.pre_prod_cleanup_impact
python -m app.cli.pre_prod_export
python -m app.cli.pre_prod_cleanup_plan
python -m app.cli.pre_prod_isolated_cleanup
python -m app.cli.full_market_rebuild
python -m app.cli.rebuild_b3_historical_market
python -m app.cli.sync_treasury_catalog_v2
python -m app.cli.rebuild_treasury_official_prices
```

## Prioridades atuais

1. Planejar, revisar e aprovar separadamente a limpeza controlada da pré-produção real no escopo da Issue #158.
2. Executar a limpeza e o rebuild pré-produção somente após todos os novos gates operacionais.
3. Endurecer ou remover o router administrativo de debug antes do go-live.
4. Remover o serviço legado de rentabilidade (#151).
5. Materializar o histórico persistido do IBOV (#150).
6. Implementar TWR dedicado para Tesouro Direto e Renda Fixa (#149).
7. Migrar timestamps UTC legados para timezone-aware (#192).

## Dependências

A auditoria Dependabot da Issue #159 foi concluída. Atualizações compatíveis foram incorporadas em blocos isolados e não há PR Dependabot aberta após a promoção da PR #198.

## Pré-produção

A primeira entrada em produção exige:

1. inventário read-only aprovado — concluído;
2. backup validado e restauração isolada — concluído;
3. dry-run read-only e relatório de impacto — concluído;
4. exportação controlada das tabelas obrigatórias — concluído;
5. plano de execução validado sem acesso ao banco — concluído;
6. executor, CLI e artefatos auditáveis — concluído;
7. ensaio integral em banco descartável com sucesso e rollback — concluído;
8. autorização separada para limpeza na pré-produção real — pendente;
9. limpeza controlada dos dados reconstruíveis — pendente;
10. seed B3 COTAHIST — pendente;
11. seed oficial do Tesouro Direto — pendente;
12. seed de benchmarks, câmbio e proventos — pendente;
13. importação CSV completa da carteira — pendente;
14. rebuild de posições e snapshots — pendente;
15. reconciliação financeira e auditoria de cobertura — pendente.

Checklist completo: Issue #158. Runbooks: `docs/PRE_PROD_REBUILD_RUNBOOK.md`, `docs/pre-prod-cleanup-impact-runbook.md`, `docs/pre-prod-export-runbook.md`, `docs/pre-prod-cleanup-execution-runbook.md` e `docs/pre-prod-isolated-cleanup-rehearsal-runbook.md`.

## Stack

Backend: Python 3.12, FastAPI, SQLAlchemy async, Alembic, PostgreSQL, Redis e APScheduler.

Frontend: React 19, TypeScript, Vite, TailwindCSS 4, Recharts, React Query, Zustand e Axios.

## Como rodar

```bash
cp .env.example .env
docker compose up -d --build
```

## Documentação viva

- `ROADMAP.md` — prioridades e andamento modular.
- `ROADMAP_SPRINTS.md` — histórico de sprints.
- `CHANGELOG.md` — mudanças relevantes.
- `docs/architecture.md` — arquitetura DB-first.
- `docs/providers.md` — fontes e fallbacks.
- `docs/operations.md` — operação e rebuilds.
- `docs/PRE_PROD_REBUILD_RUNBOOK.md` — política e sequência do rebuild pré-produção.
- `docs/pre-prod-cleanup-impact-runbook.md` — dry-run e critérios de aborto.
- `docs/pre-prod-export-runbook.md` — exportação e reconciliação.
- `docs/pre-prod-cleanup-execution-runbook.md` — plano e execução controlada.
- `docs/pre-prod-isolated-cleanup-rehearsal-runbook.md` — ensaio isolado, rollback e descarte.
- `docs/CANONICAL_FINANCIAL_CONTRACT.md` — contrato financeiro oficial.
