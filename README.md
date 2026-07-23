# SGI v2 — Sistema de Gestão de Investimentos

Plataforma pessoal para acompanhamento, consolidação e análise de investimentos, com backend FastAPI e frontend React + TypeScript.

A branch padrão de desenvolvimento é `stable-15jun`. A promoção para `main` ocorre por PR após validação e atualização da documentação viva.

## Status atual — 23/07/2026

O SGI v2 opera com arquitetura **DB-first**: catálogo, preços, taxas, proventos e snapshots são persistidos antes de alimentar KPIs, páginas e gráficos.

A revisão arquitetural integral de 23/07/2026 está em
`docs/ARCHITECTURAL_REVIEW_2026-07-23.md`. A prontidão estimada para a primeira
produção é 88%; o ensaio reconciliado da limpeza isolada e a restauração do CI
da PR #198 são bloqueadores P0. A limpeza da base real continua proibida.

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
- Página Resumo concluída, reconciliada com valuation e snapshots canônicos e promovida pela PR #164.
- Fase 2 de Proventos concluída sob a Issue #165 e promovida pela PR #166: pipeline DB-first, contratos estritos, filtros compartilhados, coleta global e materialização rastreável.
- Histórico mensal de proventos reconciliado por classe, com detalhamento acessível por mouse, teclado e toque.
- Fase 3 de Patrimônio concluída sob a Issue #148: históricos consolidados e por classe, períodos determinísticos, tooltips canônicos e reconciliações observáveis por base temporal.
- Valuation intradiário reconciliado entre `summary.v2`, posições e distribuição; snapshots consolidados reconciliados com classes somente na mesma data.
- Inventário pré-produção read-only validado no PostgreSQL real, com 24 tabelas, política completa de classificação e contrato `pre-prod-inventory.v2`.
- Backup `pre-prod-backup.v3` validado no PostgreSQL real com cliente/servidor 16/16, snapshot único `REPEATABLE READ READ ONLY`, dump com SHA-256, restauração em banco vazio e isolado e reconciliação `ok=true`, sem divergências e com zero escritas na origem. A Issue #183 foi concluída e a PR #184 promovida para a `main`.
- Dry-run de limpeza validado no PostgreSQL real pelo contrato `pre-prod-cleanup-impact.v2`: 24 tabelas, 4.673.320 linhas, 11 preservadas, 3 com exportação obrigatória, 10 reconstruíveis, zero bloqueios, zero ciclos e zero escritas. A execução `20260722-101848` retornou `ok=true` e exit code `0`.
- Exportação auditável `pre-prod-export.v1` validada no PostgreSQL real em snapshot único `REPEATABLE READ READ ONLY`: `corporate_events`, `fixed_income_investments` e `transactions` reconciliadas em 323 linhas, com SHA-256 de dados e schema, zero escritas na origem e `reconciled=true`. A execução `20260722-134741` retornou exit code `0`, a Issue #188 foi encerrada e a PR #191 promovida para a `main`.
- Fundação plan-only da limpeza promovida pela PR #194: contrato `pre-prod-cleanup-execution.v1`, CLI `pre_prod_cleanup_plan`, verificação integral de identidade, checksums, gate e DAG, publicação atômica de `cleanup/plan.json`, persistência atômica de `cleanup-impact.json` e rollback de exportação incompleta.
- Executor e CLI da limpeza isolada implementados na Issue #196 e na PR #198: lock operacional, validação de contagens, transação única, rollback integral, relatórios `committed`, `aborted` e `rolled_back`, publicação atômica e logs redigidos. A validação multiplataforma passou com 44 testes e `compileall` sem erros.
- Runbook D0 do ensaio em PostgreSQL descartável concluído, com gates, comandos PowerShell, reconciliação, cenário obrigatório de rollback e descarte do banco. Nenhuma limpeza real foi executada.
- Migração integral das configurações Pydantic v2 para `ConfigDict` concluída na Issue #186. A suíte dedicada passou com 5 testes e a validação final registrou `666 passed`, `1 skipped` intencional e zero `PydanticDeprecatedSince20`.

### Tesouro Direto — Blocos 3.1 e 3.2

O fluxo usado pela página Resumo foi alinhado ao pipeline canônico:

- provedor primário de mercado para preços recentes;
- dados abertos oficiais do Tesouro como fallback;
- último preço persistido como contingência;
- resolução case-insensitive de tickers e aliases;
- preço devolvido pelo ticker original da posição;
- criação automática de ativos duplicados bloqueada;
- regressões para RendA+ adicionadas.

Os valores atuais de Selic e RendA+ foram validados na interface. A limpeza integral da base foi adiada para o checklist pré-produção e está registrada na issue #158.

## Arquitetura resumida

```text
Importação CSV / lançamentos manuais
        ↓
Transações
        ↓
Catálogo canônico de ativos
        ↓
B3 COTAHIST | dados abertos oficiais do Tesouro | séries macroeconômicas | motores dedicados
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

1. Implementar captura automática e reconciliação das tabelas preservadas para o ensaio isolado da Issue #196.
2. Executar os cenários de sucesso e rollback somente em PostgreSQL descartável restaurado do backup v3.
3. Promover a PR #198 após validação integral do bloco estrutural.
4. Executar a limpeza e o rebuild pré-produção em etapas auditáveis somente após aprovação do ensaio isolado.
5. Remover o serviço legado de rentabilidade (#151).
6. Materializar o histórico persistido do IBOV (#150).
7. Implementar TWR dedicado, separando Tesouro Direto e Renda Fixa (#149).
8. Migrar timestamps UTC legados para timezone-aware (#192).

## Dependências

A auditoria Dependabot da Issue #159 foi concluída. Atualizações compatíveis foram incorporadas à `stable-15jun` em blocos isolados. A incompatibilidade entre TypeScript 7 e `typescript-eslint@8.64.0` foi corrigida pela Issue #182, mantendo resolução estrita de peer dependencies. Não há PR Dependabot aberta após o merge da PR #194.

## Pré-produção

A primeira entrada em produção exige:

1. inventário read-only aprovado e sem tabelas desconhecidas — concluído;
2. backup validado com checksum e restauração isolada — concluído pela Issue #183;
3. dry-run read-only da limpeza e relatório de impacto — validado pela Issue #185;
4. exportação controlada das transações, renda fixa e eventos corporativos — validada pela Issue #188 e promovida pela PR #191;
5. plano de execução `pre-prod-cleanup-execution.v1` validado sem acesso ao banco — concluído pela Issue #195 e PR #194;
6. executor, CLI e artefato da limpeza isolada — implementados pela Issue #196 e PR #198, com 44 testes aprovados;
7. ensaio integral em banco descartável, incluindo sucesso, rollback e reconciliação de tabelas preservadas — pendente;
8. limpeza controlada de dados reconstruíveis na pré-produção real — não autorizada nesta fase;
9. seed B3 COTAHIST;
10. seed oficial do Tesouro Direto;
11. seed de benchmarks, câmbio e proventos;
12. importação CSV completa da carteira;
13. rebuild de posições e snapshots;
14. reconciliação financeira e auditoria de cobertura.

Checklist completo: issue #158. Runbook geral: `docs/PRE_PROD_REBUILD_RUNBOOK.md`. Runbook do dry-run: `docs/pre-prod-cleanup-impact-runbook.md`. Runbook da exportação: `docs/pre-prod-export-runbook.md`. Runbook da execução: `docs/pre-prod-cleanup-execution-runbook.md`. Runbook do ensaio isolado: `docs/pre-prod-isolated-cleanup-rehearsal-runbook.md`.

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
- `docs/pre-prod-cleanup-impact-runbook.md` — execução, artefato, exit codes e critérios de aborto do dry-run.
- `docs/pre-prod-export-runbook.md` — execução read-only, artefatos, manifesto, reconciliação e códigos de saída da exportação.
- `docs/pre-prod-cleanup-execution-runbook.md` — validação plan-only, cadeia de artefatos, plano e códigos de saída.
- `docs/pre-prod-isolated-cleanup-rehearsal-runbook.md` — gates, restauração, execução, rollback, reconciliação e descarte do ensaio isolado.
- `docs/CANONICAL_FINANCIAL_CONTRACT.md` — contrato financeiro oficial.
- `docs/RESUMO_ARCHITECTURAL_AUDIT.md` — matriz de contratos e divergências da página Resumo.
- `docs/PROVENTOS_ARCHITECTURAL_AUDIT.md` — fluxo, contratos, riscos e sequência da Fase 2.
- `docs/PATRIMONIO_ARCHITECTURAL_AUDIT.md` — snapshots, históricos por classe e reconciliações da Fase 3.
