# SGI v2 — Sistema de Gestão de Investimentos

Plataforma pessoal para acompanhamento, consolidação e análise de investimentos, com backend FastAPI e frontend React + TypeScript.

A branch padrão de desenvolvimento é `stable-15jun`. A promoção para `main` ocorre por PR após validação e atualização da documentação viva.

## Status atual — 28/07/2026

O SGI v2 opera com arquitetura **DB-first**: catálogo, preços, taxas, proventos e snapshots são persistidos antes de alimentar KPIs, páginas e gráficos.

A PR #202 foi promovida para a `main` e unificou a árvore Alembic no merge `6ee96b003a8c6bf4955b906687faf17d99e7ed09`. A Issue #199 é o gate operacional ativo para a limpeza controlada da pré-produção real.

A cadeia operacional `20260724-135540`, vinculada ao merge `4c306c7d755470093e492ed7bb9432c28b935232`, validou backup v3, exportação de 326 registros, impacto e plano de 4.673.920 remoções sem blockers, ciclos ou escritas. A revisão identificou que a saída do gerador não expunha o checksum canônico exigido pela confirmação composta. A CLI agora publica `plan_sha256` no envelope de saída, usando exatamente a serialização revalidada pela limpeza. Como essa correção altera o SHA executável, a cadeia `20260724-135540` permanece evidência técnica e não pode autorizar a limpeza.

A limpeza real, seeds B3/Tesouro, proventos, importação e rebuild ainda não foram executados. Os seeds isolados de benchmarks macroeconômicos e câmbio já foram executados e tiveram idempotência comprovada operacionalmente.

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
- Perfil isolado `sgi-pre-prod-isolated`: exige origem e destino diferentes.
- Perfil real `sgi-pre-prod-real`: exige origem e destino com a mesma identidade normalizada.
- Perfil real promovido para a `main` pela PR #204.
- Wrapper PowerShell oficial para a execução real, sem comandos aninhados ou reconstrução da confirmação.
- Checksum canônico `plan_sha256` exposto oficialmente pelo gerador do plano.
- Evidências automáticas: `preserved-before.json`, `preserved-after.json`, `post-cleanup-inventory.json`, `reconciliation.json` e `cleanup/execution.json`.
- Ensaio de sucesso `20260723-213000`: 4.673.054 linhas planejadas removidas, tabelas preservadas inalteradas e `reconciliation.ok=true`.
- Ensaio de rollback `20260723-213001`: exit code `22`, nenhuma escrita persistida e `reconciliation.ok=true`.
- Validação local do perfil real: 34 testes aprovados e `compileall` sem erros.
- Migração Pydantic v2 concluída pela Issue #186.
- CLI transacional `pre_prod_treasury_seed` implementada pela Issue #208, com advisory lock, baseline, commit único, rollback integral, identidade obrigatória (`run_id`, branch e SHA) e contrato `pre-prod-treasury-seed.v1`; execução real permanece pendente.
- Comparador puro e CLI offline de idempotência do Tesouro implementados na PR #211 com o contrato `pre-prod-treasury-seed-idempotency.v1`.
- Wrapper `scripts/Invoke-PreProdTreasuryIdempotency.ps1` implementado na PR #212 para executar duas evidências consecutivas, preservar os artefatos e acionar o comparador offline com gates de branch, SHA, confirmação explícita e caminhos host/container reconciliados.
- Seed isolado de benchmarks implementado com contrato `pre-prod-macro-seed.v1`, advisory lock, transação única, CLI e wrapper PowerShell.
- Execuções `20260725-231557` e `20260725-231604` comprovaram estado final estável, zero novas linhas, zero duplicidades e zero indicadores não suportados.
- Comparador `pre-prod-macro-seed-compare.v1` e persistidor `scripts/compare_pre_prod_macro_seed.ps1` preservam a prova offline em JSON auditável.
- Seed isolado de câmbio implementado pela Issue #217 com contrato `pre-prod-fx-seed.v1`, inspeção read-only, cliente PTAX estrito, persistência transacional, advisory lock, CLI auditável e runbook dedicado.
- Execuções `20260728-103750` e `20260728-104238`, no commit `37c1d800be6f21dfc5c91b332a6ebe8748c0ac1c`, comprovaram estado final estável em 6 linhas, zero novas linhas na segunda execução, zero duplicidades, zero pares não suportados e `ok=true`.

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
scripts/Invoke-PreProdRealCleanup.ps1
python -m app.cli.pre_prod_b3_seed --start-year <ANO> --end-year <ANO> --cutoff-date <AAAA-MM-DD>
python -m app.cli.pre_prod_treasury_seed --run-id <YYYYMMDD-HHMMSS> --branch stable-15jun --commit-sha <SHA40>
python -m app.cli.pre_prod_treasury_seed_idempotency --first <PRIMEIRA_EVIDENCIA.json> --second <SEGUNDA_EVIDENCIA.json>
scripts/Invoke-PreProdTreasuryIdempotency.ps1 -CommitSha <SHA40> -Confirmation EXECUTE-TREASURY-IDEMPOTENCY:<SHA40>
scripts/pre_prod_macro_seed.ps1 -RunId <YYYYMMDD-HHMMSS> -Branch stable-15jun -CommitSha <SHA40>
scripts/compare_pre_prod_macro_seed.ps1 -FirstEvidence <PRIMEIRA_EVIDENCIA.json> -SecondEvidence <SEGUNDA_EVIDENCIA.json> -RunId <YYYYMMDD-HHMMSS>
python -m app.cli.pre_prod_fx_seed --run-id <YYYYMMDD-HHMMSS> --branch stable-15jun --commit-sha <SHA40> --start-date <AAAA-MM-DD> --end-date <AAAA-MM-DD>
python -m app.cli.full_market_rebuild
python -m app.cli.rebuild_b3_historical_market
python -m app.cli.sync_treasury_catalog_v2
python -m app.cli.rebuild_treasury_official_prices
```

As CLIs isoladas de B3, Tesouro, benchmarks e câmbio não autorizam execução na pré-produção real apenas por estarem disponíveis. Cada estágio exige SHA aprovado, janela operacional, evidência preservada e reconciliação na Issue correspondente. Os comparadores de idempotência operam somente sobre arquivos JSON e não acessam banco ou rede.

## Prioridades atuais

1. Promover a exposição do `plan_sha256` e gerar uma nova cadeia operacional vinculada ao novo SHA.
2. Registrar nova confirmação composta e executar a limpeza real somente pela Issue #199.
3. Executar e reconciliar os seeds isolados de B3 e Tesouro em blocos separados após a limpeza.
4. Implementar e validar o estágio isolado de proventos.
5. Executar importação e rebuild em blocos independentes.
6. Endurecer ou remover o router administrativo de debug antes do go-live.
7. Remover o serviço legado de rentabilidade (#151).
8. Materializar o histórico persistido do IBOV (#150).
9. Implementar TWR dedicado para Tesouro Direto e Renda Fixa (#149).
10. Migrar timestamps UTC legados para timezone-aware (#192).

## Dependências

A auditoria Dependabot da Issue #159 foi concluída. Atualizações compatíveis foram incorporadas em blocos isolados e não há PR aberta no fechamento deste bloco.

## Pré-produção

A primeira entrada em produção exige:

1. inventário read-only aprovado — concluído;
2. backup validado e restauração isolada — concluído;
3. dry-run read-only e relatório de impacto — concluído;
4. exportação controlada das tabelas obrigatórias — concluído;
5. plano de execução validado sem acesso ao banco — concluído;
6. executor, CLI e artefatos auditáveis — concluído;
7. ensaio integral em banco descartável com sucesso e rollback — concluído;
8. perfil explícito e testado para a pré-produção real — concluído e promovido pela PR #204;
9. nova cadeia de artefatos vinculada ao SHA promovido — validada em `20260724-135540`, mas invalidada para execução pela correção posterior do checksum;
10. nova autorização composta — pendente;
11. limpeza controlada dos dados reconstruíveis — pendente;
12. entrypoint isolado de catálogo + B3 COTAHIST — implementado, execução pendente;
13. entrypoint transacional do seed oficial do Tesouro Direto — implementado com identidade obrigatória; comparador e wrapper de idempotência implementados; execução e evidência real pendentes;
14. seed isolado de benchmarks — executado e idempotência comprovada;
15. seed isolado de câmbio — executado e idempotência comprovada pela Issue #217;
16. seed isolado de proventos — pendente;
17. importação CSV completa da carteira — pendente;
18. rebuild de posições e snapshots — pendente;
19. reconciliação financeira e auditoria de cobertura — pendente.

Checklist completo: Issue #158. Gates operacionais: Issues #199, #208 e #216. A Issue #217 foi encerrada após a prova de idempotência cambial. Runbooks: `docs/PRE_PROD_REBUILD_RUNBOOK.md`, `docs/pre-prod-cleanup-impact-runbook.md`, `docs/pre-prod-export-runbook.md`, `docs/pre-prod-cleanup-execution-runbook.md`, `docs/pre-prod-isolated-cleanup-rehearsal-runbook.md`, `docs/pre-prod-real-cleanup-target-profile.md`, `docs/pre-prod-treasury-seed-runbook.md`, `docs/pre-prod-macro-seed-runbook.md` e `docs/pre-prod-fx-seed-runbook.md`.

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
- `docs/pre-prod-real-cleanup-target-profile.md` — gates dos perfis isolado e real.
- `docs/pre-prod-treasury-seed-runbook.md` — seed transacional, integridade, evidência, wrapper e prova offline de idempotência do Tesouro.
- `docs/pre-prod-macro-seed-runbook.md` — seed transacional de benchmarks, evidência, persistência da comparação e prova operacional de idempotência.
- `docs/pre-prod-fx-seed-runbook.md` — seed PTAX estrito, transação, evidência e prova operacional de idempotência cambial.
- `docs/CANONICAL_FINANCIAL_CONTRACT.md` — contrato financeiro oficial.
