# #158 - validacao read-only do dataset restaurado

## Contexto

O artefato `20260915-002119` foi restaurado com sucesso em
`sgi_restore_20260915_002119`. Este bloco executou somente validacoes read-only
sobre esse banco isolado.

## Gates

`pre-prod-inventory.v2`:

- 20 tabelas;
- 4.434.818 linhas;
- 7 tabelas preservadas;
- 2 tabelas `export_before_cleanup`;
- 11 tabelas reconstruiveis;
- 0 tabelas sem classificacao;
- 0 findings bloqueantes;
- `read_only=true`;
- `writes_executed=0`;
- `cleanup_executed=false`;
- `rebuild_executed=false`.

`user-test-readiness.v1`:

- `status=GO_ASSISTED`;
- `go_for_assisted_user_tests=true`;
- `ready_for_real_data=false`;
- blockers: nenhum;
- warnings: nenhum;
- `promotes_ready_for_real_data=false`;
- `allows_real_user_data=false`.

## Dataset observado

Carteiras:

- 6 carteiras;
- 7 usuarios;
- 366 transacoes;
- carteira 15: 354 transacoes entre 22/10/2024 e 13/09/2026;
- carteira 13: 11 transacoes sinteticas entre 02/01/2026 e 20/02/2026;
- carteira 17: 1 transacao de cripto em 09/09/2026.

Ledger:

- compras: 306;
- vendas: 60.

Snapshots:

- `portfolio_snapshots`: 608;
- `portfolio_class_snapshots`: 5.121;
- carteira 13: 107 snapshots consolidados, 1.103 snapshots por classe;
- carteira 15: 496 snapshots consolidados, 4.013 snapshots por classe;
- carteira 17: 5 snapshots consolidados, 5 snapshots por classe.

Ultimo snapshot por carteira:

- carteira 13 em 29/05/2026: patrimonio 38.960,00; custo 37.629,30; resultado
  total 1.781,50; proventos acumulados 20,00;
- carteira 15 em 15/09/2026: patrimonio 13.894,37; custo 14.075,72; resultado
  total -74,12; proventos acumulados 559,69;
- carteira 17 em 15/09/2026: patrimonio 363.880,00; custo 369.580,00;
  resultado total -5.700,00; proventos acumulados 0,00.

Cobertura:

- carteira 13: 61 dias com precos parciais e 62 retornos estimados;
- carteira 15: 39 dias com precos parciais e 39 retornos estimados;
- carteira 17: 4 dias com precos parciais e 4 retornos estimados.

## Deltas materiais

### Eventos corporativos

`corporate_events` possui 123 linhas:

- 122 `PENDENTE/UNRECONCILED/requires_review=true`;
- 1 `APLICADO/UNRECONCILED/requires_review=true`.

Esse e o principal delta material antes do GO. A #158 deve decidir quais eventos
afetam materialmente o dataset e reconciliar/bloquear somente esses casos.

### Tesouro

Foram observados pares legado/canonico no ledger, com quantidades liquidas
opostas ou complementares:

- `TESOURO-RENDA-MAIS-2060`: -3;
- `tesouro-renda-mais-2060`: 3;
- `TESOURO-RENDA-MAIS-2065`: -2;
- `tesouro-renda-mais-2065`: 2;
- `TESOURO-SELIC-01032031`: -0,04;
- `tesouro-selic-01032031`: 0,04.

O achado foi registrado na #365 e nao autoriza normalizacao destrutiva nem
feature da Trilha B durante a #158.

### IRPF

Nao existem tabelas fisicas `irpf*` no schema restaurado. A validacao deve usar
os servicos runtime suportados e nao recriar tabelas legadas.

## Decisao

O banco restaurado passou nos gates read-only gerais. A #158 deve prosseguir
com reconciliation read-only focada nos deltas materiais: eventos corporativos,
Tesouro, cobertura parcial/retornos estimados e IRPF runtime.

Continuam bloqueados:

- import/rebuild;
- cleanup real;
- migration destrutiva;
- seed global por conveniencia;
- promocao de `ready_for_real_data=true`.
