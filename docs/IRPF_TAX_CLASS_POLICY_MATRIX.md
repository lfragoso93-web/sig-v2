# Matriz de políticas fiscais por classe — IRPF

> Estado: desenho de contrato anterior à correção do motor mensal  
> Issue: #56  
> Branch: `stable-15jun`

## Objetivo

Impedir que o motor de IRPF derive regras tributárias de agrupamentos técnicos amplos. Cada classe deve resolver uma política fiscal explícita antes da apuração mensal.

A projeção financeira canônica fornece baixas realizadas, custo, receita, taxas, moeda e eventos. Esta matriz pertence somente à camada fiscal.

## Dimensões obrigatórias da política

Cada classe fiscal deve declarar:

- identificadores de ativo aceitos;
- grupo de apuração da operação comum;
- grupo de apuração Day Trade;
- elegibilidade e limite de isenção mensal;
- alíquota de operação comum;
- alíquota de Day Trade;
- grupo de compensação de prejuízo comum;
- grupo de compensação de prejuízo Day Trade;
- regra de retenção na fonte;
- tratamento cambial;
- situação de suporte do SGI.

Bases, isenções e prejuízos somente podem ser combinados quando a política declarar o mesmo grupo fiscal.

## Matriz inicial

| Classe SGI | Operação comum | Day Trade | Isenção mensal | Compensação | Retenção | Estado no SGI |
|---|---:|---:|---|---|---|---|
| Ações no mercado à vista | 15% | 20% | Até R$ 20 mil de alienações mensais para o conjunto de ações; não se aplica a Day Trade | Comum separada de Day Trade | Deve ser modelada | Regra parcial; agregação atual precisa ser segregada |
| BDR | 15% | 20% | Não elegível à isenção de ações | Comum separada de Day Trade | Deve ser modelada | Anomalia: atualmente incluído em `_ACAO_TYPES` e tratado como isento |
| ETF | 15% | 20% | Não elegível | Comum separada de Day Trade | Deve ser modelada | Regra parcial; hoje pode ter base reduzida por isenção de ações |
| FII / Fiagro negociado em bolsa | 20% | Política específica a validar antes da implementação | Não elegível | Grupo próprio; perdas não devem reduzir ações/ETF/BDR | Deve ser modelada | Anomalia: atualmente usa 15% comum e grupo agregado |
| Ativos negociados no exterior | Política dependente do regime e ano-calendário | Não presumir regra doméstica | Não reutilizar automaticamente a isenção de ações brasileiras | Grupo próprio conforme regime aplicável | Conforme regime | Pendente de requisito jurídico/versionamento temporal |
| Renda fixa / Tesouro | Fora do motor mensal de renda variável | Não aplicável | Não aplicável | Não aplicável | Tributação própria na fonte | Fora deste motor |
| Criptoativos | Ganho de capital, fora do demonstrativo de bolsa | Não aplicável | Política de bens de pequeno valor conforme legislação vigente e período | Grupo próprio | Não aplicável como bolsa | Fora do primeiro corte desta Issue |

## Regras arquiteturais

1. Não usar conjuntos como `_ACAO_TYPES` para compartilhar automaticamente isenção, alíquota ou prejuízo.
2. Resolver a política por classe antes de agregar qualquer venda.
3. Segregar operação comum de Day Trade mesmo dentro da mesma classe.
4. Casar Day Trade quantitativamente por ativo, data e intermediário quando essa informação existir.
5. Manter prejuízos acumulados por grupo fiscal e modalidade.
6. Representar retenção na fonte separadamente do imposto devido.
7. Recusar classe sem política suportada em vez de aplicar fallback silencioso.
8. Versionar regras que dependam do ano-calendário.
9. Não realizar consultas externas durante a apuração; câmbio deve vir de fonte persistida ou resultar em ausência explícita.
10. Relatórios devem expor resultados por classe e também uma visão consolidada reconciliável.

## Anomalias vigentes já caracterizadas

- BDR recebe indevidamente a isenção mensal de ações.
- A isenção é subtraída do lucro agregado, em vez de excluir somente os ganhos das operações efetivamente isentas.
- Lucros e perdas de classes diferentes compartilham a mesma base Swing.
- FII usa a alíquota Swing genérica de 15%.
- Prejuízos não são transportados corretamente entre meses.
- Day Trade é detectado por presença de compra e venda na data/ticker, sem casamento quantitativo.
- Retenções permanecem zeradas.
- Venda acima da posição é aceita pelo leitor fiscal legado.
- Câmbio admite consulta externa e fallback `USD/BRL = 1.0`.

## Ordem de implementação

1. Criar tipos e resolver políticas por classe, ainda sem trocar o cálculo público.
2. Adicionar testes de contrato para o catálogo fiscal.
3. Provar equivalência contábil entre baixas canônicas e cenários Swing suportados.
4. Migrar a origem contábil de `calc_ganhos_capital` para baixas canônicas.
5. Corrigir, em commits independentes: BDR, FII, segregação de bases, prejuízos, Day Trade quantitativo, retenções e câmbio.
6. Expor visões mensais por classe e consolidado reconciliado.

## Fontes de validação

A implementação deve ser baseada em fontes oficiais vigentes da Receita Federal e normas aplicáveis ao respectivo ano-calendário. Esta matriz é um contrato arquitetural e não substitui validação tributária profissional.
