# Direitos financeiros por fracoes de bonificacao

## Contrato de leitura

O endpoint `GET /portfolios/{portfolio_id}/corporate-events/rights` calcula valores por carteira em modo DB-first. Para cada evento global, somente `MATCHED`, canonico, sem revisao e com evidencia `MATCHED`, calcula a posicao do ledger na `record_date`, aplica as proporcoes por componente, separa quantidades inteiras de fracionarias e multiplica cada fracao pelo preco publicado daquele componente. A data de disponibilidade vem de `corporate_events.payment_date`. Nenhuma transacao historica ou linha de provento e criada.

A evidencia persistida no `raw_metadata` segue o contrato: `fractional_component_settlement.model=COMPONENT_BONUS_FRACTIONS_V1`, `evidence_reference`, `bonus_factor`, `cash_treatment` e `components[]` com `component`, `units_per_position` e `settlement_price_brl`. Para Units compostas, `unit_composition` declara as quantidades exigidas de cada componente (por exemplo, `{"ON": 1, "PN": 4}`). O leitor ignora eventos incompletos, sem referencia de fonte ou que nao satisfazem o gate de reconciliacao. O DTO devolve por componente a quantidade total, as inteiras, as fracionarias, Units completas formadas e a sobra inteira por especie. O montante e um calculo bruto derivado e vem marcado `CALCULATED_NOT_CONFIRMED`; data passada significa apenas disponibilidade segundo emissor, nao prova de pagamento individual. O read model nao altera posicao, custo, realizado, snapshots, TWR ou IRPF.

## KLBN11

O aviso da Klabin informa bonificacao de 1% por especie. Para Units, as acoes sao agrupadas na proporcao 1 ON + 4 PN para formar novas Units; se nao for possivel formar Unit, as acoes sao creditadas diretamente. As fracoes de acoes remanescentes sao agrupadas, leiloadas e o produto liquido e distribuido proporcionalmente. O SGI nao trata o residuo como fracao de KLBN11.

Para 10 Units na data-base, a regra produz 0,10 ON e 0,40 PN fracionarias. Com os valores oficiais do leilao, o calculo nao arredondado e `0,10 * 3,942352337 + 0,40 * 3,942611212 = R$ 1,9712797185`. A data de disponibilidade informada pela Klabin e 24/02/2026. O sistema conserva precisao decimal; eventual arredondamento para pagamento ao titular deve ocorrer uma unica vez no limite de moeda.

Fontes primarias: [aviso oficial do leilao](https://api.mziq.com/mzfilemanager/v2/d/1c41fa99-efe7-4e72-81dd-5b571f5aa376/4c7d2a8f-0e01-a99f-c100-6f7e2737a216?origin=2), [aviso oficial da bonificacao](https://api.mziq.com/mzfilemanager/v2/d/1c41fa99-efe7-4e72-81dd-5b571f5aa376/19213371-ea1d-5182-207b-13f387751cfe?origin=1), [composicao de KLBN11](https://ri.klabin.com.br/para-o-investidor/perguntas-frequentes/).

## Gate pendente para ativacao

Os eventos locais 81/82 continuam `CONFLICT`; o endpoint nao os apresenta como direitos aplicados. A integracao financeira multiativo foi implementada na timeline compartilhada: quantidade por componente, Units e acoes residuais entram nas leituras de posicao, custo/realizado, resumo, snapshots/TWR, lifecycle e IRPF. As fracoes leiloadas sao direitos calculados por carteira e seguem `CALCULATED_NOT_CONFIRMED`; nao viram caixa recebido ou retorno realizado sem fato de pagamento confirmado.

O gate de ativacao exige que o evento canonico contenha o contrato completo em `raw_metadata.fractional_component_settlement`, com a referencia documental coincidente com a evidencia MATCHED e identidades ISIN resolvidas no catalogo. O preflight especializado calcula as pernas em modo read-only. Ainda e necessario executar esse preflight com o banco/catalogo atuais e aprovar separadamente qualquer escrita de reconciliacao; nenhum runtime ou banco foi alterado neste bloco.
## Integracao da timeline multiativo - 20/10/2026

`project_transaction_timelines()` agora expande uma acao com
`component_bonus` validado em movimentos derivados em memoria. A posicao-base
vem da timeline ate `record_date`; Units inteiras e acoes residuais recebem o
custo atribuido do emissor, e vendas posteriores usam esse custo no resultado
realizado e nos leitores de Bens e Direitos. As pernas destino entram no mesmo
resultado por ticker/ativo consumido por posicao atual, resumo, snapshots de
classe, valuation/TWR, lifecycle, IRPF e preflight. Nenhuma `Transaction` e
criada nem alterada.

As fracoes vendidas geram `component_bonus_cash_rights` com quantidade, preco,
valor bruto, custo atribuido e resultado estimado. Permanecem
`CALCULATED_NOT_CONFIRMED`: nao viram posicao negociavel, caixa recebido,
resultado realizado ou fluxo de TWR antes de existir fato de pagamento. O
endpoint portfolio-scoped exibe tambem o custo atribuido e o resultado
estimado por componente.

O leitor exige evidencia oficial com referencia igual a registrada no evento,
ISINs resolvidos no catalogo e o contrato completo. A reconciliacao tambem
exige essa referencia; o preflight especializado calcula pernas e direitos em
modo read-only e permanece `ready_for_execution=false`. Os eventos locais
81/82 continuam `CONFLICT`; nao foram gravados eventos, transacoes ou
snapshots.

A Klabin atribuiu R$ 12,94564988922 por acao bonificada. Essa informacao consta
no [aviso oficial de bonificacao](https://api.mziq.com/mzfilemanager/v2/d/1c41fa99-efe7-4e72-81dd-5b571f5aa376/19213371-ea1d-5182-207b-13f387751cfe?origin=1).
