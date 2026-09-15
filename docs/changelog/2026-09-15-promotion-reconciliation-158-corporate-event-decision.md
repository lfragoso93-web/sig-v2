# #158 - decisao sobre eventos corporativos materiais

Data: 2026-09-15
Branch: `stable-15jun`
Banco restaurado: `sgi_restore_20260915_002119`

## Objetivo

Decidir o delta de eventos corporativos materiais encontrado na reconciliation
read-only da #158 antes de qualquer GO, import, rebuild ou cleanup real.

## Evidencia

O contrato runtime de `corporate_action_position_reader` autoriza projecao
somente para eventos globais elegiveis:

- `is_canonical=true`;
- `reconciliation_status=MATCHED`;
- `requires_review=false`.

Eventos `UNRECONCILED/requires_review=true` permanecem fora da projecao
financeira, preservando fail-closed.

## Resultado da decisao

Foram cruzados os 15 eventos inicialmente materiais com o ledger real da
carteira 15 na data de cada evento.

Eventos que permanecem bloqueantes por haver exposicao positiva no evento:

| Ticker | Evento | Data | Fonte | Quantidade na data |
| --- | --- | --- | --- | --- |
| AMOB3 | BONIFICACAO | 2025-05-28 | brapi | 6 |
| AMOB3 | GRUPAMENTO | 2025-05-29 | yahoo | 6 |
| KLBN11 | BONIFICACAO | 2025-12-17 | brapi | 10 |
| KLBN11 | DESDOBRAMENTO | 2025-12-18 | yahoo | 10 |

Os outros 11 eventos revisados ocorreram com quantidade zero na data do evento.
`POMO4` tem posicao final de 30 unidades, mas os eventos de dezembro/2025
ocorreram depois da zeragem em 24/06/2025 e antes das recompras de abril/2026,
sem afetar a posicao aberta atual pelo projetor canonico.

## Governanca

Foi criada a Issue #370 para tratar a reconciliacao ou descarte formal dos 4
eventos bloqueantes antes do GO da #158.

Enquanto #370 estiver aberta, permanecem bloqueados:

- avancar #158 para #269/#284/#227;
- abrir PR estrutural `stable-15jun` -> `main`;
- promover `ready_for_real_data=true`;
- aplicar eventos pendentes por atalho;
- mutar transacoes historicas;
- criar fonte paralela de posicao, custo ou lifecycle.

## Validacao executada

- consulta read-only dos campos de elegibilidade dos eventos corporativos;
- consulta read-only do ledger de `AMOB3`, `FIQE3`, `GOAU4`, `ITSA4`,
  `KLBN11`, `KLBN4`, `PETZ3` e `POMO4`;
- consulta read-only de quantidade antes/no evento e quantidade final por
  ticker;
- revisao do contrato `corporate_action_position_reader`;
- revisao da cobertura existente em
  `tests/test_corporate_action_projection_eligibility.py`.
