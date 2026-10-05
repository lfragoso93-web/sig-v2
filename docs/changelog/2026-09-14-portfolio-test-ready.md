# 2026-09-14 - PORTFOLIO-TEST-READY

## Decision

Issue #303 is ready to be closed as `PORTFOLIO-TEST-READY`.

This decision consumes:

- recovered backend technical gates from #363;
- closed password-policy drift from #354;
- closed and manually validated class/type selector from #352;
- accumulated synthetic portfolio, CSV, snapshot, restart, persistence, IRPF,
  Tesouro, Renda Fixa, Proventos portfolio-scoped and UI evidence already
  recorded in #303 and the certification documents.

## Boundary

This is not a production GO.

The following remain closed until their own gates complete:

- `ready_for_real_data=true`;
- broad real-data usage;
- global or destructive real-data operations;
- structural PR `stable-15jun` -> `main`.

## Next Track A Gate

The next canonical block is #226, using the existing portfolio-scoped Proventos
evidence to decide whether it is sufficient for promotion or whether a controlled
global run is materially required.
