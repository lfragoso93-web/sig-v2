# #158 - reconciliation read-only focada

## Contexto

O bloco anterior aprovou os gates gerais read-only do banco restaurado
`sgi_restore_20260915_002119`, mas deixou deltas materiais para eventos
corporativos, Tesouro, cobertura parcial e IRPF runtime.

Este bloco executou somente consultas e CLIs read-only.

## Eventos corporativos

Estado bruto:

- 123 eventos corporativos;
- 122 globais `PENDENTE/UNRECONCILED/requires_review=true`;
- 1 evento de carteira `APLICADO/UNRECONCILED/requires_review=true`.

Materialidade para carteira 15:

- todos os 122 eventos globais pertencem a tickers presentes na carteira 15;
- 14 eventos globais estao dentro da janela de exposicao da carteira 15;
- 108 eventos globais ocorreram antes da primeira transacao do respectivo
  ticker e nao foram classificados como materiais neste bloco;
- o evento de carteira e `TICKER_CHANGE` de `PETZ3` em 05/01/2026.

Eventos materiais:

- `AMOB3`: bonificacao e grupamento em maio/2025;
- `FIQE3`: bonificacao e desdobramento em dezembro/2025;
- `GOAU4`: bonificacao e desdobramento em dezembro/2025;
- `ITSA4`: bonificacao e desdobramento em dezembro/2025;
- `KLBN11`: bonificacao e desdobramento em dezembro/2025;
- `KLBN4`: desdobramento em dezembro/2025;
- `PETZ3`: bonificacao em 02/01/2026 e ticker change aplicado em 05/01/2026;
- `POMO4`: bonificacao e desdobramento em dezembro/2025.

`POMO4` e o unico ticker material com posicao liquida aberta observada no
ledger da carteira 15: 30 unidades. Os demais tickers materiais estao zerados,
mas ainda podem afetar historico, custo, snapshots e IRPF.

## Tesouro

A auditoria read-only `audit_treasury_canonical_assets` retornou:

- 152 ativos;
- 151 grupos canonicos;
- 0 grupos duplicados;
- 0 candidatos de migracao;
- `unresolved=[]`;
- `destructive_changes=false`.

O achado de pares legado/canonico observado no bloco anterior permanece
registrado na #365, mas nao houve novo blocker operacional no auditor atual.

## IRPF

A CLI `irpf_annual_assessment` emitiu contrato
`irpf-annual-assessment.v1` para a carteira 15:

- ano 2025: imposto bruto total 13,85; imposto liquido total 13,52; pagamento
  total 13,52; retencao total 0,33;
- ano 2026: imposto bruto total 11,33; imposto liquido total 11,21; pagamento
  total 11,21; retencao total 0,12.

Nao existem tabelas fisicas `irpf*` no schema restaurado; a validacao segue pelo
runtime suportado.

## Decisao

O principal delta antes do GO e a decisao dos 15 eventos corporativos materiais.
A #158 deve decidir se eles ja estao refletidos no ledger/snapshots ou se exigem
Issue especifica antes da promocao.

Continuam bloqueados:

- import/rebuild;
- cleanup real;
- migration destrutiva;
- seed global por conveniencia;
- promocao de `ready_for_real_data=true`.
