# 2026-09-14 - Rebaseline da promotion reconciliation #158

## Estado

A #158 passa a ser o gate corrente da Trilha A depois do fechamento de #303,
#226 e #216.

## Decisao operacional

A promotion reconciliation deve executar somente o delta necessário sobre
SHA/dataset congelados. Evidências já certificadas não devem ser repetidas por
checklist histórico.

## Fronteiras

- Não executar seed global de Proventos sem finding material novo.
- Não executar `full_market_rebuild` amplo como substituto da reconciliação.
- Não executar importação, rebuild, migration física ou contração destrutiva sem
  gate explícito, backup aplicável e evidência registrada na #158.
- Eventos corporativos materiais ao dataset devem ser reconciliados antes do GO.

## Próximo passo

Preparar e executar a reconciliation mínima da #158, registrando SHA, dataset,
contagens, restart, persistência, idempotência e pendências antes do security
gate #269.
