# Eventos corporativos

## Objetivo

Manter quantidade, custo médio, patrimônio e rentabilidade corretos após
renomes, splits, grupamentos, bonificações e subscrições, sem alterar operações
históricas nem usar posições materializadas como fonte contábil.

## Arquitetura canônica

O fluxo é dividido em três responsabilidades:

1. provedores externos produzem eventos globais normalizados;
2. `corporate_events` preserva o catálogo global e a evidência do provedor;
3. o motor puro projeta quantidade e custo para uma data, a partir das
   operações originais e dos eventos globais aplicáveis.

Eventos globais não pertencem a uma carteira. `portfolio_id` permanece nulo
nesses registros. Direitos e efeitos por carteira são calculados sob demanda.

## Fontes

- BRAPI v2 `/stocks/dividends`: bonificações (`stockDividends`) e direitos de
  subscrição (`subscriptions`);
- Yahoo `actions`: splits e grupamentos publicados como fatores de quantidade;
- resolução de ticker existente: renomes simples 1:1, mantidos em fluxo
  separado enquanto a identidade global de ativos é consolidada.

A rota BRAPI de dividendos não declara splits/grupamentos no contrato OpenAPI
atual. Esses eventos não são inferidos a partir de preços ou proventos; entram
por uma fonte que publique explicitamente o fator.

## Convenção de fator

Todo evento automático usa `quantity_factor`:

```text
quantidade_depois = quantidade_antes × quantity_factor
```

Exemplos:

- split 2 para 1: `2`;
- grupamento 1 para 20: `0.05`;
- bonificação de 2% publicada como fator total: `1.02`.

O custo total é preservado e o preço médio é derivado novamente. Subscrições
criam direitos, mas nunca aumentam quantidade automaticamente.

## Idempotência e auditoria

A identidade do evento inclui fonte, ticker, tipo, data, fator e identificadores
publicados. O hash determinístico é persistido na chave técnica existente
`brapi_event_id`, inclusive para fontes diferentes da BRAPI por compatibilidade
de schema.

Cada `raw_data` preserva:

- fonte e identificador canônico;
- ticker, data, tipo e fator normalizados;
- payload original do provedor.

## Segurança operacional

O scheduler apenas coleta e confirma o catálogo global. A aplicação automática
legada foi removida porque mutava `portfolio_positions` e tentava inserir
colunas incompatíveis em `transactions`. Nenhum evento é marcado como aplicado
globalmente e nenhuma operação técnica é criada pela coleta.

Cada ativo é processado em savepoint próprio. Uma falha de provedor ou
normalização não confirma um evento parcial daquele ativo e não invalida os
demais ativos já coletados na execução.

## Próximos blocos

- integrar a projeção pura aos leitores canônicos de posição e rentabilidade;
- reconciliar eventos equivalentes publicados por mais de uma fonte;
- incorporar fusões, conversões e incorporações com troca de ativo;
- criar inspeção, simulação e execução controlada do catálogo global;
- adicionar tela administrativa e revisão manual para eventos complexos.
