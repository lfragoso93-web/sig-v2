# Auditoria de ingestão de eventos monetários do Tesouro Direto

> Estado: leitura e desenho fail-closed; não autoriza seed, backfill ou
> alteração de `transactions`.
>
> Atualizado em: 09/10/2026

## Objetivo

Definir a fronteira para cupons, amortizações e vencimentos do Tesouro Direto
antes de qualquer escrita em `asset_dividends`. O TWR por classe lê somente
eventos globais já persistidos e direitos derivados do ledger; ele não consulta
provider em runtime nem calcula fluxos a partir do PU.

## Fonte oficial examinada

O conjunto oficial [Resgates do Tesouro Direto](https://www.tesourotransparente.gov.br/ckan/api/3/action/package_show?id=resgates-do-tesouro-direto)
publica recursos separados de cupons, vencimentos e recompras. Os CSVs de
cupons e vencimentos possuem:

```text
Tipo Titulo;Vencimento do Titulo;Data Resgate;PU;Quantidade;Valor
```

O metadado oficial define `PU` como preço unitário no resgate e `Data Resgate`
como a data a que o registro se refere. Assim, título + vencimento resolve a
identidade econômica conhecida, `Data Resgate` pode ser data de pagamento e
`PU` pode ser valor bruto por unidade. `Quantidade` e `Valor` são agregados do
programa e jamais representam a posição de uma carteira do SGI.

## Decisão por recurso

| Recurso oficial | Informação factual aceita | Persistência atual | Motivo |
|---|---|---|---|
| Cupom de juros | título, vencimento, data de pagamento e PU | bloqueada | não contém data de elegibilidade (`record_date`) do investidor |
| Vencimentos | título, vencimento, data de pagamento e PU | bloqueada | além de não conter elegibilidade, exige encerrar a posição sem mutar o ledger |
| Recompras | dado agregado por título/dia | proibida | resgate antecipado é fato individual já pertencente a `transactions` |
| calendário público de eventos | agenda indicativa | não persistir isoladamente | não fornece valor por unidade nem evidência de elegibilidade individual |

O Tesouro Direto também documenta que pagamentos de cupom e de vencimento são
disponibilizados no próprio dia, mas isso não define qual posição histórica da
carteira é elegível. O adaptador canônico de direitos exige `record_date` e
rejeita eventos monetários sem esse marco; não é permitido substituí-lo por
`Data Resgate`, data anterior estimada ou nome do título.

## BRAPI verificada como complemento, não como fonte de evento

A documentação da [API de Tesouro da BRAPI](https://brapi.dev/docs/tesouro-direto)
declara somente catálogo, indicadores atuais e histórico diário de taxas/preços.
Em 09/10/2026, uma leitura pública de um título com juros semestrais retornou
`couponType`, `maturityDate`, `baseDate`, taxas e preços, mas não retornou
valor de pagamento, data de pagamento, amortização, `record_date` nem regra de
elegibilidade. Portanto, a BRAPI pode enriquecer metadados de catálogo, mas não
supre o fato financeiro ausente e não é fallback para persistir eventos em
`asset_dividends`.

## Contrato já existente

Quando todos os campos forem documentados, a persistência permanece no contrato
canônico existente:

```text
fonte oficial auditável
        -> asset_dividends (RENDIMENTO ou AMORTIZACAO)
        -> direito por carteira derivado de transactions
        -> PortfolioClassSnapshot / TWR
```

Não será criada tabela de fluxo por carteira. A identidade econômica existente
de `asset_dividends` (ativo, data ex, tipo, pagamento efetivo e valor unitário)
continua sendo a proteção contra duplicidade; o payload bruto deverá preservar
URL/recurso, título, vencimento, data de pagamento, PU e instante de coleta.

## Gatilhos obrigatórios para implementação

Uma futura ingestão requer, antes de qualquer `--execute`:

1. fonte oficial que informe a regra ou data de elegibilidade por evento;
2. mapeamento auditado entre título + vencimento e o ativo canônico, incluindo
   aliases históricos;
3. política explícita de vencimento: encerrar projeção por fato de liquidação
   comprovado, sem criar ou editar `transactions` automaticamente;
4. parser puro com fixtures oficiais, rejeitando coluna ausente, PU não
   positivo, símbolo ambíguo e evento sem elegibilidade;
5. dry-run que informe candidatos, conflitos, rejeições e
   `database_writes_executed=0`; somente após autorização específica poderá
   escrever exclusivamente em `asset_dividends`;
6. reconciliação posterior de snapshots/TWR em ambiente isolado e identidade
   explícita.

Até esses requisitos serem atendidos, ausência de evento monetário permanece
explícita. É proibido inferir cupom/amortização pela variação de PU, por taxa
contratada ou pelo volume agregado do programa.
