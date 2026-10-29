# Catálogo e Índice da Documentação — SGI v2

Este diretório centraliza os documentos de especificação, governança, arquitetura e runbooks operacionais do Sistema de Gestão Financeira Pessoal (SGI v2).

---

## 1. Visão Geral e Arquitetura Central

* [`DOCUMENTACAO_DO_SISTEMA.md`](DOCUMENTACAO_DO_SISTEMA.md) — Documento mestre de referência completa do sistema, requisitos de negócio, arquitetura e stack.
* [`architecture.md`](architecture.md) — Contratos arquiteturais fundamentais, boundaries e regras de isolamento de carteiras.
* [`ARCHITECTURE_DOCTOR.md`](ARCHITECTURE_DOCTOR.md) — Especificação do Architecture Doctor (`python -m app.doctor`), catálogo de regras `SGI001` a `SGI015` e modos de verificação.
* [`ACCESS_CONTEXT.md`](ACCESS_CONTEXT.md) — Especificação formal do `PortfolioAccessContext`, permissões granulares e autorização de leitura/escrita.
* [`DETERMINISTIC_RUNTIME.md`](DETERMINISTIC_RUNTIME.md) — Princípios de determinismo temporal, injeção de `Clock` canônico e isolamento de dependências externas.
* [`portfolio-route-hierarchy.md`](portfolio-route-hierarchy.md) — Hierarquia e isolamento das rotas `/carteira/{id}/*` no frontend e backend.

---

## 2. Modelagem Financeira Canônica e Proventos

* [`CANONICAL_FINANCIAL_CONTRACT.md`](CANONICAL_FINANCIAL_CONTRACT.md) — Contrato canônico de posições, saldo e regras de liquidação.
* [`canonical-data.md`](canonical-data.md) — Modelo canônico de dados, persistência e regras de transações.
* [`DIVIDENDS_CANONICAL_ARCHITECTURE.md`](DIVIDENDS_CANONICAL_ARCHITECTURE.md) — Arquitetura de proventos, eventos em dinheiro vs. ações e liquidação.
* [`PROVENTOS_ARCHITECTURAL_AUDIT.md`](PROVENTOS_ARCHITECTURAL_AUDIT.md) — Auditoria arquitetural das rotas de proventos e unificação de superfícies.
* [`PROVENTOS_MODEL_MIGRATION_PLAN.md`](PROVENTOS_MODEL_MIGRATION_PLAN.md) — Plano de migração do modelo legado para o modelo canônico de proventos.
* [`snapshots.md`](snapshots.md) — Snapshots diários de patrimônio e cálculo de rentabilidade ponderada pelo tempo (TWR).
* [`rentabilidade.md`](rentabilidade.md) — Métricas de rentabilidade (TWR diário, MWR/TIR e benchmarks comparativos).
* [`FIXED_INCOME_TAXONOMY_INVENTORY.md`](FIXED_INCOME_TAXONOMY_INVENTORY.md) — Taxonomia de renda fixa, regras de indexadores e marcação na curva.
* [`TREASURY_CASH_FLOW_CONTRACT.md`](TREASURY_CASH_FLOW_CONTRACT.md) — Contrato de fluxo de caixa e cupons do Tesouro Direto.

---

## 3. Eventos Corporativos e Desdobramentos

* [`CORPORATE_ACTIONS.md`](CORPORATE_ACTIONS.md) — Especificação de eventos corporativos (grupamentos, desdobramentos, bonificações, incorporações).
* [`CORPORATE_ACTIONS_IMPLEMENTATION_STATUS.md`](CORPORATE_ACTIONS_IMPLEMENTATION_STATUS.md) — Matriz de conformidade da implementação de eventos corporativos.
* [`CORPORATE_EVENT_COMPLEX_ACTIONS_DESIGN.md`](CORPORATE_EVENT_COMPLEX_ACTIONS_DESIGN.md) — Design para tratamento de frações e eventos complexos.
* [`FRACTIONAL_COMPONENT_RIGHTS_DESIGN.md`](FRACTIONAL_COMPONENT_RIGHTS_DESIGN.md) — Tratamento contábil de frações residuais de ativos.

---

## 4. Motor Fiscal e IRPF Canônico

* [`IRPF_ANNUAL_ASSESSMENT_CONTRACT.md`](IRPF_ANNUAL_ASSESSMENT_CONTRACT.md) — Contrato de apuração anual e declaração de ajuste anual.
* [`IRPF_ANNUAL_ASSESSMENT_SERVICE.md`](IRPF_ANNUAL_ASSESSMENT_SERVICE.md) — Especificação do serviço de apuração anual.
* [`IRPF_CANONICAL_ENDPOINT.md`](IRPF_CANONICAL_ENDPOINT.md) — Especificação dos endpoints `/api/v1/portfolios/{id}/irpf/*`.
* [`IRPF_TAX_CLASS_POLICY_MATRIX.md`](IRPF_TAX_CLASS_POLICY_MATRIX.md) — Matriz de tributação por classe de ativo, limites de isenção e day trade.
* [`IRPF_WITHHOLDING_POLICY.md`](IRPF_WITHHOLDING_POLICY.md) — Política de retenção de imposto na fonte (dedo-duro).
* [`IRPF_MINIMUM_PAYMENT_ACCUMULATION.md`](IRPF_MINIMUM_PAYMENT_ACCUMULATION.md) — Acumulação de DARF abaixo do limite mínimo de R$ 10,00.

---

## 5. Provedores de Mercado e Ingestão de Dados

* [`providers.md`](providers.md) — Catálogo de provedores de mercado (B3, BCB SGS, BRAPI, Tesouro Transparente, Yahoo Finance).
* [`PROVIDER_ACCESS_POLICY_2026-08.md`](PROVIDER_ACCESS_POLICY_2026-08.md) — Governança de credenciais, timeouts e failover entre provedores.
* [`B3_COTAHIST_DATA_AUTHORITY.md`](B3_COTAHIST_DATA_AUTHORITY.md) — Autoridade do arquivo oficial COTA HIST da B3.
* [`price-history.md`](price-history.md) — Modelo de persistência e histórico de preços de fechamento (`asset_prices`).
* [`MARKET_CALENDAR_CONTRACT.md`](MARKET_CALENDAR_CONTRACT.md) — Calendário oficial de negociação e dias úteis da B3.
* [`CSV_IMPORT_PIPELINE.md`](CSV_IMPORT_PIPELINE.md) — Pipeline de importação assistida de extratos de corretoras e B3.

---

## 6. Operações, Governança e Certificação

* [`operations.md`](operations.md) — Guia de operações em produção, agendador em background e comandos do sistema.
* [`ISSUE_GOVERNANCE.md`](ISSUE_GOVERNANCE.md) — Políticas de branches (`stable-15jun` -> `main`), Pull Requests e CI/CD.
* [`REAL_DATA_CERTIFICATION_RUNBOOK.md`](REAL_DATA_CERTIFICATION_RUNBOOK.md) — Procedimento de auditoria e certificação de datasets reais (`/ready`).
* [`ADMIN_BACKUP_RESTORE_REHEARSAL.md`](ADMIN_BACKUP_RESTORE_REHEARSAL.md) — Procedimento de backup e restauração de dados.
* [`USER_VALIDATION_RUNBOOK.md`](USER_VALIDATION_RUNBOOK.md) — Runbook de validação de funcionalidades com usuários.
* [`DIAGNOSTICO_OPORTUNIDADES_MELHORIA.md`](DIAGNOSTICO_OPORTUNIDADES_MELHORIA.md) — Relatório diagnóstico de oportunidades de melhoria (Fases 1 a 4).
