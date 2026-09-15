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

## Simulacao read-only de impacto

Os 4 eventos bloqueantes foram simulados com `project_position_timeline`, sem
alterar dados persistidos e sem mudar o estado de reconciliacao dos eventos.

| Ticker | Cenario | Quantidade final | Custo final | Realizado |
| --- | --- | ---: | ---: | ---: |
| AMOB3 | sem eventos | 0 | 0 | -4,20 |
| AMOB3 | aplicando eventos pendentes | 0 | 0 | -86,966880 |
| KLBN11 | sem eventos | 0 | 0 | 1,70 |
| KLBN11 | aplicando eventos pendentes | 0,2010 | 3,6511420448975590628369768 | 5,3511420448975590628369768 |

Conclusao: a #370 nao deve ser tratada como simples promocao de eventos
`UNRECONCILED` para `MATCHED`. O delta exige reconciliacao economica de fonte,
fator, data efetiva e tratamento de fracao/residuo antes de qualquer rebuild
seletivo.

## Classificacao tecnica dos eventos

Leitura read-only dos metadados brutos mostrou:

- `AMOB3` BRAPI: `label=GRUPAMENTO`, `completeFactor="1 para 50"` e fator
  `0.02`, embora o evento estivesse persistido como `BONIFICACAO`;
- `AMOB3` Yahoo: `GRUPAMENTO` com fator `0.02` no dia seguinte;
- `KLBN11` BRAPI: `BONIFICACAO`, `completeFactor="1,01 para 1"` e fator
  `1.01`;
- `KLBN11` Yahoo: `DESDOBRAMENTO` com fator `1.01` no dia seguinte.

Foi aplicada uma correcao preventiva no normalizador BRAPI para respeitar labels
explicitos `GRUPAMENTO` e `DESDOBRAMENTO` em `stockDividends`. A correcao evita
novos eventos com classificacao semantica errada, mas nao altera eventos ja
persistidos nem promove eventos pendentes.

`AMOB3` e `KLBN11` continuam exigindo reconciliacao de duplicidade economica
entre fontes antes de qualquer evento ser marcado como `MATCHED`.

## Plano de reconciliacao economica

Simulacao por fonte isolada confirmou que nenhuma das quatro evidencias pode ser
marcada como `MATCHED` com seguranca no dataset candidato:

| Ticker | Cenario | Quantidade final | Custo final | Realizado |
| --- | --- | ---: | ---: | ---: |
| AMOB3 | sem eventos | 0 | 0 | -4,20 |
| AMOB3 | somente BRAPI corrigido para `GRUPAMENTO` | 0 | 0 | -85,3440 |
| AMOB3 | somente Yahoo `GRUPAMENTO` | 0 | 0 | -85,3440 |
| KLBN11 | sem eventos | 0 | 0 | 1,70 |
| KLBN11 | somente BRAPI `BONIFICACAO` | 0,10 | 1,8346534653465346534653465 | 3,5346534653465346534653465 |
| KLBN11 | somente Yahoo `DESDOBRAMENTO` | 0,10 | 1,8346534653465346534653465 | 3,5346534653465346534653465 |

Decisao: os 4 eventos devem permanecer fora da projecao financeira e tratados
como conflito/revisao manual ate haver reconciliacao contra extrato ou politica
canonica de fracao/residuo. Esse plano nao executa rebuild seletivo nem altera
estado persistido dos eventos.

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
