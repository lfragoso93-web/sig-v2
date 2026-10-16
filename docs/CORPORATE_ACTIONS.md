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
- Yahoo `actions`: fonte complementar/fallback para fatores de splits e
  grupamentos quando a BRAPI estiver indisponível ou retornar resultado válido
  vazio; cada provedor mantém identidade e payload próprios;
- B3: evidência oficial independente para fator/data de eventos listados; não
  substituir silenciosamente payloads Yahoo/BRAPI nem sintetizar um fato entre
  fontes;
- classes cobertas pela coleta: ações, BDRs, FIIs e ETFs nacionais e
  internacionais; cripto, Tesouro Direto e renda fixa ficam fora deste fluxo;
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

### Liquidação de frações

Quando a quantidade fracionária e o fator estiverem comprovados, mas o preço
ou crédito do leilão ainda não estiver disponível, a evidência pode usar
`PENDING_SETTLEMENT`. Nesse estado:

- o fator é aplicado; somente a quantidade inteira permanece na posição negociável,
  enquanto quantidade fracionária e custo proporcional ficam registrados como
  pendência do evento;
- o read model informa a quantidade e `PENDING_VALUE`;
- não há preço, caixa, custo de alienação ou resultado realizado inferido;
- a parcela fracionária não entra na quantidade negociável nem na valorização
  da carteira; apenas o custo proporcional da quantidade inteira permanece
  investido na posição;
- snapshots marcam a classe como incompleta com
  `pending_corporate_action_fraction` enquanto essa parcela estiver pendente;
- o custo proporcional da fração permanece anexado à pendência, sem baixa ou
  realização, até que evidência de liquidação permita atualizar o evento para
  `CASH_SETTLEMENT`.

Quando um evento elegível produz quantidade fracionária e a evidência de
reconciliação declara `CASH_SETTLEMENT`, o motor:

- mantém somente a quantidade inteira na posição;
- aloca à fração a parcela proporcional do custo da posição projetada;
- registra separadamente o caixa bruto recebido e o custo alocado;
- reconhece `caixa bruto - custo alocado` no resultado realizado financeiro;
- preserva esse realizado nos snapshots e trata o crédito de caixa como
  distribuição no TWR, sem convertê-lo em aporte ou retirada;
- não cria uma `Transaction` artificial nem classifica automaticamente o fluxo
  como alienação fiscal.

Quantidade fracionária, preço efetivo de liquidação e tratamento de caixa devem
vir de evidência operacional. Ausência desses dados mantém o evento fail-closed.

## Idempotência e auditoria

A identidade do evento inclui fonte, ticker, tipo, data, fator e identificadores
publicados. O hash determinístico é persistido na chave técnica existente
`brapi_event_id`, inclusive para fontes diferentes da BRAPI por compatibilidade
de schema.

Cada `raw_data` preserva:

- fonte e identificador canônico;
- ticker, data, tipo e fator normalizados;
- payload original do provedor.

### Candidatos cross-provider

A descoberta de equivalências considera somente eventos ainda `UNRECONCILED`
com ativo, tipo, data efetiva e fator exatamente iguais entre ao menos duas
fontes. O resultado é candidato para revisão; igualdade desses campos não prova
identidade econômica e nunca marca linhas como `MATCHED` nem altera a projeção.
Datas ou fatores divergentes continuam fora do grupo e exigem análise própria.

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
