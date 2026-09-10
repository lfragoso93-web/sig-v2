# 2026-09-10 - Primeira limpeza de performance em Rentabilidade

## Contexto

Os testes assistidos deixaram claro que rebuilds de snapshots e rentabilidade
estavam demorando mais do que o aceitavel. A auditoria inicial mostrou dois
problemas: consultas repetidas em loops diarios e contratos legados ainda
apontando para o antigo backfill.

## Mudancas

- Adicionado calculo de Renda Fixa a partir de transacoes ja carregadas em
  memoria.
- O rebuild por classe passa a reutilizar essas transacoes, evitando nova
  consulta de Renda Fixa por dia util.
- Produtos `PREFIXADO` deixam de consultar referencias de benchmark no fallback.
- Testes de transacao, certificacao TWR, reconciliacao de Rentabilidade e
  fixture sintetico agora refletem `RENDA_FIXA` como TWR dedicado disponivel.

## Validacao

- `pytest tests/test_fixed_income_valuation_from_transactions.py tests/test_portfolio_class_snapshot_service.py tests/test_transaction_snapshot_invalidation_contract.py tests/test_portfolio_twr_availability_certification.py tests/test_rentabilidade_reconciliation_service.py tests/test_portfolio_synthetic_certification_fixture.py::test_synthetic_fixture_surfaces_partial_twr_by_design`
  retornou `14 passed`.

## Proximos Alvos

- Unificar ou aposentar os servicos legados `portfolio_snapshot_service` e
  `portfolio_snapshot_twr_service` que ainda existem como suporte parcial.
- Reduzir o rebuild consolidado diario, que ainda recalcula posicoes e Tesouro
  a cada data.
- Revisar os mocks antigos do fixture CSV, que falham por contrato de
  importacao/crypto eligibility desatualizado.
