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

- B3: fonte oficial prioritaria para eventos corporativos e fatores de ativos
  listados; preservar o documento/payload oficial e sua identidade;
- BRAPI v2 `/stocks/dividends`: fonte complementar somente para campos/eventos
  que a B3 nao publicar para o ativo; nao substitui resposta B3 valida;
- Yahoo `actions`: fallback explicitamente identificado para fatores de split e
  grupamento somente quando a fonte oficial nao tiver cobertura; nunca mesclar
  valores/datas de provedores distintos em um evento sintatico;
- classes cobertas pela coleta: aaaes, BDRs, FIIs e ETFs nacionais e
  internacionais; cripto, Tesouro Direto e renda fixa ficam fora deste fluxo;
- resoluaao de ticker existente: renomes simples 1:1, mantidos em fluxo
  separado enquanto a identidade global de ativos a consolidada.

O adaptador B3 usa os dados estruturados do portal Listed Companies para ações
nacionais e BDRs, preservando o payload oficial, ISIN e identidade da fonte.
`lastDatePrior` representa o último dia com direito; não determina sozinho o
pregão efetivo. A data efetiva é a primeira sessão aberta da B3 após
`lastDatePrior`, comprovada pelo calendário operacional oficial. Enquanto essa
evidência não estiver persistida, `effective_date` permanece nulo e o registro
fica `PENDENTE`, `UNRECONCILED` e fora da projeção. `event_date`/`record_date`
preservam a data informada pela B3 para busca e auditoria, mas nunca substituem
a data canônica efetiva.

A rota BRAPI de dividendos nao declara splits/grupamentos no contrato OpenAPI
atual. Esses eventos nao sao inferidos a partir de preaos ou proventos; entram
por fonte que publique explicitamente o fator.

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

- somente a quantidade inteira permanece na posição negociável, enquanto a
  quantidade fracionária fica registrada como pendência do evento;
- o read model informa a quantidade e `PENDING_VALUE`;
- a quantidade fracionária é calculada por carteira a partir do ledger e do fator
  do evento; ela não é armazenada como quantidade global no evento;
- o Patrimônio apresenta a fração em pendência de liquidação, com valor
  "A confirmar", até existir evidência do crédito;
- não há preço, caixa, custo de alienação ou resultado realizado inferido;
- a parcela fracionária não entra na quantidade negociável nem na valorização
- da carteira; o custo total permanece na posição até existir evidência do
  crédito, evitando baixa ou realização sem liquidação;
- snapshots marcam a classe como incompleta com
  `pending_corporate_action_fraction` enquanto essa parcela estiver pendente;
- a pendência não recebe valor de mercado nem baixa de custo até que evidência
  de liquidação permita atualizar o evento para `CASH_SETTLEMENT`.

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

- concluir a revisão e validação do bloco local de evidência de data efetiva,
  plano de reconciliação e projeção de frações pendentes; ele ainda não tem SHA
  publicado nem certificação de runtime;
- preservar KLBN11 em `CONFLICT` até existir evidência de custodiante/corretora
  para quantidade, preço de liquidação e tratamento de caixa;
- coletar os dividendos B3 faltantes de NIKE34 por ativo, com identidade e
  proveniência, sem disparar seed global;
- migrar o leitor paralelo de IRPF para a projeção canônica e rever compatibilidade
  dos fallbacks históricos;
- completar a confirmação da reconciliação cross-provider e do scheduler oficial;
- manter fusões, conversões, revisão administrativa e ferramentas complexas
  como evolução posterior, sem misturá-las ao candidato operacional atual.

## Estado de publicação — 16/10/2026

O branch publicado está em `b37661921e3a8455f45c8b676b28955d6ad3d0ea` e o
working tree contém alterações locais adicionais para reconciliação fracionária.
O container ativo não corresponde ao checkout: `/health=200`, `/ready=503` por
`runtime_identity_error`, sem referência de dataset. Não tratar as alterações
locais como implantadas. Para o retrato completo, consulte
`docs/DEVELOPMENT_BASELINE_2026-10-16.md`.

O bloco local de evidência de data efetiva, plano de reconciliação, projeção de
frações pendentes e apresentação de pendências ainda precisa de revisão e
validação antes de receber SHA de candidato. KLBN11 permanece em `CONFLICT` até
evidência de custodiante/corretora para quantidade, preço de liquidação e
tratamento de caixa. A lacuna de NIKE34 deve ser tratada por ativo sob a política
B3, sem seed global e sem inferir data, caixa ou liquidação.
