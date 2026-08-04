# Desenho de integração — realizações canônicas e ganhos mensais do IRPF

> Data: 03/08/2026  
> Issues: #56 e #227  
> Estado: baixa canônica e reader por período implementados; integração fiscal pendente

## Objetivo

Definir a menor extensão segura da projeção compartilhada para que o IRPF deixe
de reconstruir posição, custo médio e resultado realizado sem deslocar regras
fiscais para o núcleo financeiro.

## Contratos disponíveis

### `load_realized_pnl_by_ticker`

O reader atual:

- lê todas as transações da carteira;
- exclui Renda Fixa;
- carrega eventos corporativos globais;
- projeta a timeline até a data corrente;
- retorna `dict[str, float]` com o resultado acumulado por ticker.

Esse contrato é adequado para consumidores consolidados de Rentabilidade, mas
não possui granularidade suficiente para o IRPF mensal.

### `PositionTimelineProjection`

A projeção pura expõe posição final, custo total, custo na moeda original,
resultado realizado acumulado e IDs de eventos aplicados. Ela limita vendas à
quantidade disponível e intercala eventos corporativos deterministicamente.

O retorno, porém, não preserva cada baixa realizada. Depois da agregação não é
possível recuperar data, quantidade, receita, custo baixado ou taxas da venda.

## Matriz de equivalência

| Necessidade do IRPF | Contrato atual | Lacuna |
|---|---|---|
| ticker | chave do mapa agregado | disponível |
| resultado realizado total | `realized_pnl` | disponível apenas acumulado |
| data da venda | não exposta | obrigatória para mês e Day Trade |
| identidade da operação | não exposta | obrigatória para auditoria |
| quantidade efetivamente baixada | não exposta | obrigatória; difere em venda acima da posição |
| receita bruta em BRL | não exposta | obrigatória para limite mensal |
| custo baixado em BRL | não exposto | obrigatória para reconciliação |
| taxas da venda | incorporadas no total | precisam permanecer auditáveis |
| classe do ativo | descartada no retorno | obrigatória para categoria fiscal |
| moeda e valores originais | apenas custo final agregado | insuficiente por venda |
| eventos aplicados | IDs agregados | falta vínculo auditável com a realização |
| Day Trade/Swing Trade | ausente corretamente | permanece responsabilidade fiscal |
| isenção, alíquota e compensação | ausentes corretamente | permanecem responsabilidade fiscal |
| retenção | ausente | requer fonte persistida e interpretação fiscal |

## Extensão mínima proposta

Criar no núcleo de projeção um registro imutável de baixa realizada, com tipos
monetários `Decimal`, sem campos ou decisões fiscais:

```text
CanonicalRealizedDisposal
├── transaction_id
├── ticker
├── asset_type
├── disposal_date
├── quantity_requested
├── quantity_disposed
├── unit_proceeds_brl
├── gross_proceeds_brl
├── cost_basis_brl
├── fees_brl
├── realized_pnl_brl
├── currency
├── gross_proceeds_original_currency
└── applied_event_ids
```

A projeção detalhada deve ser produzida no mesmo passe cronológico que já
calcula posição e realizado. Não deve existir um segundo algoritmo de baixa.
O reader agregado vigente passa a somar esses registros, preservando seu
contrato público e seus consumidores.

### Estado implementado

`CanonicalRealizedDisposal` agora é produzido por `project_position_timeline`
no mesmo passe que calcula o resultado acumulado. O registro diferencia
quantidade solicitada e efetivamente baixada, preserva receita, custo, taxas,
moeda, identidade da transação e eventos já aplicados.

`load_realized_disposals` carrega todo o histórico necessário até o fim do
período e filtra apenas as baixas do intervalo solicitado. O contrato agregado
`load_realized_pnl_by_ticker` foi preservado e passou a somar a mesma coleção de
baixas, eliminando o risco de dois algoritmos de realizado.

## Fronteiras de responsabilidade

### Núcleo financeiro

- ordenar transações e eventos deterministicamente;
- limitar a baixa à posição disponível ou produzir ausência/erro explícito;
- preservar custo e taxas com `Decimal`;
- usar câmbio persistido, sem consulta externa durante cálculo;
- expor realizações auditáveis por operação;
- preservar identidade e eventos aplicados.

### Domínio fiscal

- casar operações Day Trade por data e ativo;
- segregar classes e categorias tributárias;
- calcular limite mensal de vendas e isenções;
- transportar e compensar prejuízos por categoria;
- aplicar alíquotas, retenções e arredondamento de apresentação;
- compor `VendaMensal` e `GanhoCapitalMensal`.

## Sequência segura

1. Caracterizar a projeção vigente em venda parcial, venda acima da posição,
   eventos corporativos, taxas e moeda estrangeira — concluído.
2. Introduzir o registro detalhado puro sem integrar o IRPF — concluído.
3. Provar que a soma das baixas equivale ao `realized_pnl` agregado existente —
   concluído.
4. Expor reader por período — concluído; ausência cambial explícita permanece
   como gate da origem persistida.
5. Criar testes de equivalência entre o cálculo fiscal legado e as baixas nos
   cenários suportados.
6. Migrar somente a origem contábil de `calc_ganhos_capital` — pendente.
7. Corrigir divergências fiscais em commits posteriores e deliberados.

## Gates antes da implementação

- decidir o comportamento canônico de venda acima da posição;
- confirmar a fonte persistida de câmbio por transação;
- definir identidade estável quando a transação não possui ID persistido em
  testes ou importações;
- garantir vínculo entre troca de ticker e identidade econômica do ativo;
- validar se retenções pertencem à transação, nota de corretagem ou entidade
  fiscal dedicada;
- não remover `load_realized_pnl_by_ticker` nem a fachada do IRPF enquanto
  existirem consumidores.

## Fora deste desenho

- corrigir regras fiscais;
- alterar schemas públicos;
- executar migrations, seeds ou rebuilds;
- importar dados reais;
- implementar materialização fiscal por carteira.
