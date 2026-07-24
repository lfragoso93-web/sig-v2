# Revisão arquitetural completa — 23/07/2026

## Natureza do documento

Este documento preserva a fotografia arquitetural produzida durante a PR #198. Os achados abaixo refletem o estado observado antes do ensaio PostgreSQL descartável e antes da promoção da PR.

## Adendo pós-merge — 24/07/2026

Os bloqueadores P0 identificados nesta revisão foram posteriormente resolvidos:

- a portabilidade Windows da publicação atômica foi corrigida;
- os testes frontend obsoletos foram corrigidos;
- a captura automática de baseline, pós-contagem e tabelas preservadas foi implementada;
- os artefatos `preserved-before.json`, `preserved-after.json`, `post-cleanup-inventory.json` e `reconciliation.json` foram integrados à CLI;
- o cenário de sucesso `20260723-213000` foi reconciliado com 4.673.054 linhas planejadas removidas;
- o cenário de rollback `20260723-213001` foi reconciliado com exit code `22` e nenhuma escrita persistida;
- os bancos PostgreSQL descartáveis do ensaio foram removidos;
- os checks backend, frontend e de segurança foram aprovados;
- a PR #198 foi mergeada na `main` pelo commit `77783e46042bd32622500705cb7d365f70c728ae`;
- a Issue #196 foi encerrada como concluída.

A limpeza da pré-produção real não foi executada e permanece condicionada a uma autorização operacional separada no escopo da Issue #158.

## Escopo e conclusão original

A revisão foi executada na branch `stable-15jun`, então sincronizada com a `main`. Foram revisados arquitetura, documentação viva, contratos canônicos, CLIs e scripts operacionais, serviços, integrações, pipelines, migrations, estrutura DB-first, Issues abertas e a PR #198.

Conclusão original: o núcleo financeiro DB-first estava consolidado, mas o projeto ainda não estava pronto para produção. A prontidão aproximada era **88%** considerando o escopo da primeira produção; funcionalidades futuras não entravam no percentual.

## Estado e arquitetura

- Backend FastAPI, SQLAlchemy async, Alembic, PostgreSQL, Redis e APScheduler.
- Frontend React 19, TypeScript, Vite, React Query e Zustand.
- Contratos financeiros `summary.v2` e `rentabilidade.v2`.
- Contratos pré-produção: inventário v2, backup v3, cleanup-impact v2, export v1, cleanup-execution v1 e isolated-cleanup v1.
- DB-first aplicado a catálogo, preços, taxas, proventos e snapshots.
- 24 tabelas inventariadas: 11 preservadas, 3 exportáveis e 10 reconstruíveis.
- Backup/restauração isolada, dry-run, exportação, plano e ensaio isolado reconciliados.

```text
Entradas (CSV / lançamentos / provedores)
  -> catálogo e aliases canônicos
  -> transações e eventos
  -> séries persistidas (asset_prices / rate_history / proventos)
  -> valuation dedicado por classe
  -> snapshots consolidados e por classe
  -> contratos canônicos
  -> Resumo / Patrimônio / Rentabilidade / Proventos / IRPF
```

## Achados ainda válidos

### Alta prioridade

1. A Issue #83 diverge parcialmente da implementação: backup/restore administrativo existe, mas o restore ainda requer revisão de reautenticação, upload e auditoria no `AuditLog`.
2. O serviço legado de rentabilidade permanece dependência de produção para invalidação de cache em consumidores residuais.
3. O router administrativo de debug pode criar usuário privilegiado e redefinir senha quando habilitado; deve ser removido ou isolado antes do go-live.

### Média prioridade

4. Existem unidades grandes, incluindo integrações de mercado, router administrativo, modal de transação, serviço de portfólio, tabela de posições e serviço de IRPF.
5. Existem entradas frontend antigas ou duplicadas que devem ser consolidadas incrementalmente.
6. A migration `013_add_purchase_price_to_treasury.py` permanece fora da árvore Alembic oficial e referencia tabela removida.
7. Timestamps UTC naive permanecem registrados na Issue #192.
8. TWR dedicado para Tesouro Direto e Renda Fixa permanece pendente na Issue #149.
9. O histórico persistido do IBOV permanece pendente na Issue #150.

## Estado das Issues após o adendo

| Issue | Estado | Próxima ação |
|---|---|---|
| #196 | Concluída | Nenhuma; preservar evidências e histórico |
| #158 | Aberta, P0 e issue-mãe | Planejar autorização separada da limpeza real e rebuild |
| #192 | Aberta | Migrar timestamps para UTC timezone-aware |
| #151 | Aberta | Extrair invalidação e remover serviço legado |
| #150 | Aberta | Materializar IBOV persistido |
| #149 | Aberta | Implementar TWR diário dedicado |
| #130 | Aberta, parcial | Atualizar progresso e concluir enriquecimento |
| #129 | Aberta, parcial | Concluir motor e fontes de eventos corporativos |
| #127 | Aberta | Planejar provedores configuráveis |
| #97 | Aberta | Implementar Google OAuth |
| #90 | Aberta, parcial | Revisar UX remanescente de Patrimônio |
| #83 | Aberta, parcial | Endurecer backup/restore administrativo |
| #58 | Aberta, parcial | Completar janela global do ativo |
| #57 | Aberta, parcial | Completar análise de carteira |
| #56 | Aberta, parcial | Completar regras fiscais e testes |

## PR #198 — resultado final

- Mergeada na `main` em 23/07/2026.
- Executor transacional, CLI isolada, relatórios e reconciliação promovidos.
- Cenários de sucesso e rollback aprovados em PostgreSQL descartável.
- Backend, frontend, análise estática e verificações de segurança aprovados.
- A capacidade destrutiva permanece limitada por contrato ao alvo explicitamente isolado.
- A promoção não autoriza automaticamente execução contra pré-produção real.

## Riscos de produção remanescentes

- limpeza real sem nova autorização operacional: crítico;
- router administrativo de debug: alto;
- restore administrativo sem reautenticação/auditoria completa: alto;
- serviço legado de rentabilidade reutilizável: médio-alto;
- TWR Tesouro/RF e IBOV incompletos: médio, com ausência explícita preservada;
- timestamps naive, monólitos, duplicações e migration órfã: médio.

## Fila priorizada pós-merge

| Prioridade | Item | Impacto |
|---|---|---|
| P0 | Criar Issue de autorização da limpeza real | Separa ensaio de execução operacional |
| P0 | Atualizar a Issue #158 e runbook operacional | Mantém o rebuild auditável |
| P0 | Endurecer/remover debug router | Segurança de go-live |
| P1 | Concluir backup/restore admin #83 | Restore seguro e auditado |
| P1 | Remover legado #151 | Elimina fórmulas e cache obsoletos |
| P1 | Materializar IBOV #150 | Benchmark DB-first |
| P1 | TWR Tesouro/RF #149 | Performance por classe |
| P1 | UTC aware #192 | Coerência temporal |
| P2 | Regras fiscais #56 | Homologação IRPF |
| P2 | Consolidar frontend | Menos duplicação |
| P2 | Arquivar migration órfã | Menos ambiguidade |
| P2 | Decompor monólitos | Revisão e testabilidade |
| P2 | Cobertura/providers #129/#130 | Qualidade das integrações |
| P3 | Google OAuth #97 | Onboarding |
| P3 | Provedores configuráveis #127 | Flexibilidade futura |
| P3 | UX #90, análise #57 e ativo #58 | Evolução de produto |

## Próximos marcos

1. Sincronizar documentação e Issues após o merge da PR #198.
2. Criar Issue operacional separada para autorização da limpeza real.
3. Revisar gates, janela, novo backup, nova exportação e novo plano.
4. Executar qualquer limpeza real somente após aprovação explícita.
5. Prosseguir com seeds, importação, rebuild e reconciliação em blocos auditáveis.
