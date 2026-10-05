# 2026-09-10 - Rentabilidade com TWR canonico e Renda Fixa dedicada

## Contexto

Durante os testes assistidos, a tela Patrimonio expôs snapshots canonicos de
Renda Fixa inconsistentes e a tela Rentabilidade continuou apresentando grafico
e KPIs parciais. A carteira validada tinha snapshots recentes, mas os campos de
retorno canonico permaneciam zerados em parte dos fluxos.

## Mudancas

- Rebuilds de admin, transacoes, manutencao e full market agora usam
  `backfill_canonical_snapshots_with_returns`.
- O rebuild pos-transacao invalida o cache de Rentabilidade.
- `RENDA_FIXA` passou a participar do TWR dedicado por classe usando o motor de
  valuation por contrato/indexador.
- Lacunas de preco persistido passam a ser detectadas em mensagens acentuadas e
  em mensagens com encoding legado.
- Testes focados cobrem a disponibilidade de Renda Fixa por classe, manutencao
  TWR e deteccao de lacunas de preco.

## Validacao

- `pytest tests/test_portfolio_class_snapshot_service.py tests/test_portfolio_snapshot_twr_maintenance_service.py tests/test_portfolio_snapshot_canonical_twr_service.py`
  retornou `13 passed`.
- `pytest tests/test_portfolio_class_snapshot_service.py tests/test_portfolio_snapshot_twr_service.py tests/test_portfolio_snapshot_twr_maintenance_service.py tests/test_csv_snapshot_rebuild_service.py`
  retornou `20 passed`.
- Na carteira `15`, os snapshots consolidados chegaram a 493 linhas ate
  10/09/2026, com 492 retornos acumulados nao zerados.
- Os snapshots por classe passaram a incluir `RENDA_FIXA` com 493 linhas.
- O historico de `NU` foi reparado com 1.192 precos persistidos.

## Ressalva

`TESOURO_DIRETO` permanece limitado a cobertura oficial/exata do historico
dedicado. O sistema nao deve interpolar cotacao de Tesouro para preencher
lacunas artificiais.
