# Inventário de ganhos de capital mensais do IRPF

> Data: 02/08/2026
>
> Issue: #56
>
> Escopo: inventário e baseline; nenhuma regra fiscal alterada

## Fronteira pública atual

O contrato `list[GanhoCapitalMensal]` é produzido por
`irpf_tax_service.calc_ganhos_capital` e alcança dois consumidores de produção:

1. `GET /portfolios/{portfolio_id}/irpf/{year}/ganhos`, em
   `app/routers/irpf.py`;
2. `irpf_report_service.generate_irpf_report`, usado pelos endpoints de
   relatório, PDF e CSV.

Ambos ainda importam a função pela fachada temporária `irpf_service.py`.
Não foram encontrados consumidores em CLIs, seeds, schedulers ou jobs.

Os testes existentes exercitam a fachada, o relatório e a rota indiretamente.
Somente os cenários sem transações, compra seguida de venda simples e detecção
binária de compra/venda no mesmo dia possuem caracterização específica.

## Responsabilidades encontradas

### Reconstrução contábil a migrar

`calc_ganhos_capital` ainda executa responsabilidades que devem pertencer aos
projetores compartilhados:

- lê todas as transações anteriores ao ano para reconstruir a posição inicial;
- mantém quantidade, custo total e custo médio em memória por ticker;
- faz baixa proporcional de custo em cada venda;
- calcula resultado realizado por venda;
- trata zeragem com `max(0, quantidade)`;
- converte operações internacionais durante a projeção;
- ignora eventos corporativos na reconstrução local.

Essas responsabilidades não devem ser reimplementadas durante a migração. O
IRPF deverá consumir posição/custo/realizado canônicos por operação e período.

### Semântica fiscal a preservar no domínio IRPF

As responsabilidades que permanecem fiscais são:

- classificação Day Trade e Swing Trade;
- agrupamento por mês e categoria tributária;
- isenção mensal aplicável;
- alíquotas;
- segregação e compensação de prejuízos;
- retenções na fonte;
- arredondamento e composição do relatório.

## Comportamentos atuais que exigem caracterização

Os itens abaixo descrevem o código vigente, não regras fiscais validadas:

- Day Trade é detectado pelo par `(data, ticker)` quando existe ao menos uma
  compra e uma venda; a quantidade casada não é apurada e todas as vendas do
  par recebem a mesma classificação.
- A chave da posição é somente o ticker, sem identidade explícita de ativo,
  mercado, classe ou moeda.
- Vendas acima da posição são processadas pelo custo médio disponível e a
  quantidade final é truncada para zero, sem erro explícito.
- Taxas de compra aumentam o custo; taxas de venda reduzem o resultado. Ainda
  não há teste de rateio em operações parciais ou Day Trade.
- A isenção usa o total vendido em ações Swing Trade, mas o valor vendido é
  subtraído do lucro para formar a base; esse comportamento precisa ser
  congelado por teste antes de qualquer correção.
- O prejuízo Swing mensal é limitado a zero antes da atualização do acumulado;
  portanto, o caminho atual de acumulação precisa ser caracterizado.
- Prejuízo Day Trade não é transportado ou compensado.
- Ações, BDRs e `STOCK` compartilham a mesma categoria; demais classes Swing
  são somadas em uma única base e recebem a alíquota Swing única do contrato.
- Retenções permanecem zeradas.
- Câmbio internacional chama `price_history_service` e usa `USD/BRL=1.0` em
  ausência ou falha, contrariando a arquitetura DB-first alvo.
- Meses sem venda não aparecem na resposta.
- Arredondamentos ocorrem em níveis intermediários e na resposta final.

## Matriz mínima dos próximos testes

| Grupo | Cenários obrigatórios |
|---|---|
| Posição e custo | compra/venda, venda parcial, compras múltiplas, zeragem, recompra, venda acima da posição |
| Mensal | meses distintos, múltiplas vendas, mês sem venda, transações anteriores ao ano |
| Day Trade | casamento parcial, múltiplas operações no dia, sobra Swing, custos rateados |
| Resultado | lucro, prejuízo, compensação entre meses, separação Day Trade/Swing |
| Isenção | abaixo, igual e acima do limite; classes elegíveis e não elegíveis |
| Classes | ações, FIIs, ETFs, BDRs e exterior sem agregação indevida |
| Custos | taxas de compra e venda, venda parcial e arredondamento monetário |
| Eventos | split, grupamento, bonificação, troca de ticker e subscrição exercida |
| Câmbio | taxa persistida, taxa ausente e proibição de chamada externa/fallback 1.0 |
| Retenções | IRRF por categoria e reflexo no valor a recolher |

## Ordem segura de migração

1. Caracterizar o comportamento atual sem alterar a implementação.
2. Validar as regras fiscais esperadas e registrar divergências deliberadas.
3. Expor realização canônica por operação/período, incluindo eventos e câmbio
   persistido.
4. Substituir somente a reconstrução contábil dentro de
   `calc_ganhos_capital`, preservando o contrato público.
5. Remover a passagem pela fachada apenas após confirmar zero callers.
6. Adicionar testes arquiteturais contra reconstrução contábil e chamadas
   externas no domínio fiscal.

## Fora deste bloco

- correção de regra fiscal;
- alteração de schemas ou endpoints;
- migração para readers canônicos;
- remoção da fachada;
- carga real, seed, rebuild ou migration.
