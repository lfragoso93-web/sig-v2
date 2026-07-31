# Eventos corporativos

## Objetivo

Manter quantidade, custo médio, patrimônio, rentabilidade e direitos corretos
após eventos societários, sem editar as transações originais. O catálogo é
global: eventos não pertencem a uma carteira e seus efeitos são projetados sob
demanda para cada histórico de posição.

## Fontes validadas

- BRAPI Pro `/v2/tickers/coverage`: roteamento por capacidade;
- BRAPI Pro `/v2/tickers/resolve` e `/renames`: identidade e renomes;
- BRAPI Pro `/v2/stocks/dividends`: proventos, bonificações, subscrições,
  desdobramentos e grupamentos;
- Yahoo `Stock Splits`: fonte complementar temporária, deduplicada quando a
  BRAPI publica o mesmo evento econômico.

A auditoria real de 31/07/2026, na janela iniciada em 01/01/2000, confirmou em
PETR4 os rótulos explícitos `DESDOBRAMENTO` e `GRUPAMENTO` dentro de
`stockDividends`, com `factor`, `completeFactor`, `approvedOn`,
`lastDatePrior`, `assetIssued` e `isinCode`. O relatório sanitizado fica em
`artifacts/brapi/contract-audit-20260731.json` e não contém credenciais.

## Normalização

Todo evento de quantidade usa:

```text
quantidade_depois = quantidade_antes × quantity_factor
```

- `label=BONIFICACAO` → `BONIFICACAO`;
- `label=DESDOBRAMENTO` → `DESDOBRAMENTO`;
- `label=GRUPAMENTO` → `GRUPAMENTO`;
- `subscriptions` → `SUBSCRICAO`, sem exercício automático.

Rótulo ausente ou desconhecido é erro bloqueante. Eventos equivalentes entre
fontes são deduplicados pela identidade econômica e a BRAPI tem precedência.
Divergências não são sobrescritas silenciosamente.

## Catálogo persistente

`corporate_events` está em expansão compatível para um modelo independente de
provedor. Os campos canônicos incluem:

- fonte, identidade da fonte e hash do payload;
- hash da identidade econômica;
- ativo/ticker de origem e destino;
- tipo e estado de reconciliação/revisão;
- datas de anúncio, aprovação, registro, ex, efetivação e pagamento;
- fator de quantidade, componente financeiro e preço de subscrição;
- ISINs, moeda e metadados auditáveis.

A unicidade de coleta é `source_provider + source_event_id`. A identidade
econômica permite reconciliar duas fontes sem perder sua proveniência.
`portfolio_id`, `event_date`, `ratio`, `brapi_event_id` e `raw_data` permanecem
temporariamente apenas para compatibilidade com fluxos legados.

## Estados e segurança

Novos eventos entram como `DISCOVERED`, `UNRECONCILED` e
`requires_review=true`. Coleta não significa aplicação. O scheduler ativo só
poderá catalogar eventos após a carga controlada e não poderá aplicar eventos
ambíguos ou complexos automaticamente.

## Reconciliação entre fontes

A reconciliação é uma etapa persistente e separada da coleta:

- eventos são agrupados por ativo, ticker, tipo, data efetiva e destino;
- fator, componente financeiro e preço de subscrição compõem a identidade
  econômica usada para comparar as evidências;
- fontes independentes com identidade idêntica produzem `MATCHED`;
- a BRAPI é escolhida como representação canônica e as evidências equivalentes
  permanecem armazenadas com `is_canonical=false` e `matched_event_id`;
- fatores ou termos divergentes no mesmo grupo produzem `CONFLICT` e nenhuma
  evidência é marcada como canônica;
- evento de fonte única permanece `UNRECONCILED` e requer revisão;
- subscrições e tipos complexos exigem revisão mesmo quando as fontes concordam.

O serviço apenas altera o estado dos registros carregados e executa `flush`.
O chamador continua responsável pela transação e pelo commit.

## Sequência restante

1. persistir coverage por capacidade e TTL;
2. executar, em janela autorizada, a carga histórica controlada já implementada;
3. manter a projeção já integrada a posição, proventos, snapshots, IRPF,
   rentabilidade e performance legada;
4. eliminar o fluxo de renome por transações técnicas;
5. habilitar no scheduler ativo somente após os gates operacionais do runbook;
6. evoluir a interface administrativa já integrada com comparações detalhadas
   de payloads para eventos complexos;
7. evoluir conversões, incorporações, fusões e cisões.

A execução da carga histórica segue o runbook
`docs/CORPORATE_HISTORY_LOAD_RUNBOOK.md`. Dry-run é obrigatório e a aplicação
real depende de migration controlada, backup, autorização explícita e prova de
idempotência.

## Projeção nas posições

Os leitores de posição atual e de posições históricas usadas por valuation e
snapshots consultam somente eventos que atendem simultaneamente a todos os
gates:

- evento global (`portfolio_id` nulo);
- `is_canonical=true`;
- reconciliação `MATCHED`;
- estado `VALIDATED`;
- `requires_review=false`;
- tipo `DESDOBRAMENTO`, `GRUPAMENTO` ou `BONIFICACAO`;
- data efetiva menor ou igual à data da posição.

Os eventos são intercalados cronologicamente com compras e vendas. O fator
altera quantidade, mas preserva o custo total. Uma compra posterior a um evento
histórico não é transformada retroativamente. Conflitos, fontes únicas,
evidências equivalentes não canônicas e subscrições ficam fora do cálculo
automático.

## Direitos de proventos e IRPF

O leitor canônico de direitos intercala compras, vendas e os mesmos eventos de
quantidade elegíveis antes de calcular a posição na `record_date` (com o
fallback de data já definido pelo contrato de proventos). Assim, um
desdobramento, grupamento ou bonificação validado anterior à data de direito
altera a quantidade elegível sem duplicar nem regravar o provento global.

Em Bens e Direitos, os eventos são aplicados cronologicamente até 31/12 do ano
base. Mudanças de quantidade preservam o custo total e recalculam o custo médio;
vendas posteriores usam esse custo médio ajustado. O filtro conservador acima é
único para carteira, snapshots, direitos de proventos e IRPF, evitando que um
evento conflitante ou ainda não revisado afete qualquer desses consumidores.

## Rentabilidade e TWR por classe

O P&L realizado por ativo intercala os eventos elegíveis antes de cada venda.
Com isso, o custo médio usado na realização já reflete a nova quantidade, sem
alterar o custo total acumulado antes da venda.

A reconstrução dos snapshots TWR por classe aplica os eventos na primeira data
útil correspondente e antes das operações daquele fechamento. A alteração de
quantidade não entra em `net_external_flow`: split, grupamento e bonificação não
são aporte nem resgate. Valor de mercado, base de custo, resultado não realizado
e resultado realizado passam a derivar da posição corporativamente ajustada.

O endpoint legado de performance também deixou de reconstruir posição a partir
de somas próprias de compras e vendas. Ele consome `calc_raw_positions`, mantendo
o contrato de resposta antigo, mas herdando quantidade, base de custo, câmbio e
eventos corporativos da mesma fonte usada pelos leitores canônicos.

## Scheduler incremental

O job `sync_corporate_events_incremental` está registrado para 18:35 em dias
úteis no scheduler único `app/core/scheduler.py`. A feature flag
`CORPORATE_EVENTS_SCHEDULER_ENABLED` permanece desligada por padrão enquanto a
migration e a carga controlada não forem aprovadas.

Quando habilitado, o ciclo consulta uma janela móvel configurável, compartilha o
advisory lock com a carga histórica, isola cada ativo em savepoint, reconcilia as
fontes e confirma os sucessos mesmo que outro ativo falhe. O resultado expõe
ativos lidos, alterados e falhos, eventos criados e estados de reconciliação. O
job apenas cataloga e reconcilia; não materializa direitos por carteira.

## Revisão administrativa

A API restrita a SuperAdmin expõe a fila em
`GET /api/v1/admin/corporate-events/review` e recebe decisões em
`POST /api/v1/admin/corporate-events/{event_id}/review`. Toda decisão exige uma
justificativa entre 10 e 2.000 caracteres.

O detalhe de evidências está disponível em
`GET /api/v1/admin/corporate-events/{event_id}/evidence`. Ele retorna todas as
fontes do grupo de reconciliação, os campos econômicos comparados por ID e o
payload bruto preservado. O endpoint é somente leitura e também exige
SuperAdmin.

Aprovações humanas usam o estado explícito `MANUALLY_VALIDATED`; elas não são
registradas como `MATCHED`, pois revisão humana não equivale a consenso entre
provedores. Para conflitos, a evidência escolhida torna-se canônica e as demais
do mesmo grupo são rejeitadas. Rejeições nunca afetam posições.

O evento guarda data, usuário e justificativa da revisão, e a mesma transação
registra um `AuditLog` com valores anteriores e posteriores. Ciclos automáticos
de reconciliação não sobrescrevem decisões humanas finalizadas. A projeção aceita
`MANUALLY_VALIDATED` somente quando há revisor identificado, `status=VALIDATED`,
evento canônico e nenhum review pendente.

A interface está disponível em Configurações > Avançado > Painel Admin, na
seção “Revisão de eventos corporativos”. Ela oferece busca por ticker, filtro de
reconciliação, paginação, estados de carregamento/erro/vazio e decisões em modal.
O modal exige justificativa, mostra data, fator, fonte e tipo e alerta quando a
aprovação de um conflito rejeitará evidências concorrentes. Após a decisão, a
fila e os logs de auditoria são invalidados e recarregados.

Antes da decisão, a ação “Evidências” abre uma comparação lado a lado, destaca
campos divergentes e permite inspecionar o payload bruto de cada provedor.
Eventos complexos continuam sujeitos à revisão e não produzem efeitos
automáticos em posições neste estágio.

## Termos econômicos de eventos complexos

Antes de permitir uma aprovação, o domínio classifica o efeito econômico e
valida os termos mínimos:

- `SUBSCRICAO`: preço de subscrição positivo;
- `TICKER_CHANGE`, `CONVERSION`, `INCORPORATION`, `MERGER` e `SPINOFF`: ativo de
  destino identificável e fator de quantidade positivo;
- `AMORTIZATION`: componente em dinheiro positivo;
- `DELISTING`: componente em dinheiro ou troca completa por ativo de destino.

O diagnóstico (`economic_effect`, `terms_complete`, termos ausentes e suporte à
aplicação automática) acompanha o detalhe de evidências no Painel Admin. Um
evento incompleto não pode ser aprovado. Eventos completos desses tipos ainda
permanecem fora do projetor automático até que resolução de ativos, frações,
componentes em dinheiro e efeitos fiscais sejam implementados e testados.

## Resolução do ativo de destino e plano de troca

O ativo de destino é resolvido exclusivamente contra o catálogo local. Um ID
explícito é validado contra ticker e ISIN informados; sem ID, ticker e ISIN são
combinados e precisam apontar para exatamente um ativo. A resolução não cria
ativos, não consulta provedores durante a revisão e retorna estados explícitos
para ausência de identidade, ativo não encontrado, ambiguidade ou conflito.

Quando a aprovação de uma troca ou cisão encontra um destino inequívoco, o
vínculo `destination_asset_id` é persistido na mesma transação auditável. O
Painel Admin mostra o estado da resolução e os candidatos quando houver
ambiguidade.

O plano de projeção para `TICKER_CHANGE`, `CONVERSION`, `INCORPORATION`, `MERGER`
e `SPINOFF` calcula a quantidade de destino, a quantidade remanescente na origem
e eventual caixa total. Ele é deliberadamente `executable=false`: base de custo
não é rateada e caixa não recebe classificação fiscal implícita. Assim, o plano
serve como prova econômica e contrato para o próximo gate, sem movimentar
posições.

## Base de custo, frações e caixa

Os termos adicionais são canônicos e não inferidos do payload bruto:

- `destination_cost_allocation`: percentual do custo destinado ao novo ativo;
- `quantity_step`: passo mínimo usado para separar quantidade liquidável e
  fração;
- `fractional_settlement_price`: preço por unidade fracionária liquidada;
- `cash_treatment`: classificação revisada entre `COST_REDUCTION`,
  `TAXABLE_PROCEEDS`, `NON_TAXABLE` e `OTHER_REVIEWED`.

Trocas que encerram o ativo de origem exigem 100% do custo no destino. Cisões
exigem percentual estritamente entre zero e um, preservando o restante no ativo
de origem. Quando há passo de quantidade, um preço positivo de fração é
obrigatório. Qualquer caixa, inclusive o originado pela fração, exige tratamento
explícito antes de o plano ficar economicamente completo.

A API SuperAdmin expõe a simulação em
`POST /api/v1/admin/corporate-events/{event_id}/projection-plan`, recebendo
quantidade e custo atuais. A resposta discrimina quantidades de origem/destino,
fração, custos alocados, caixa, bloqueios e `executable`. Esse indicador significa
somente que o plano possui termos econômicos completos; o endpoint é read-only e
nenhum executor de posições está conectado a ele.

O modal de evidências oferece o mesmo cálculo em um simulador visual. O operador
informa quantidade e custo total atuais e recebe quantidade remanescente,
quantidade de destino, fração, custos alocados, caixa e bloqueios. Simular não
aprova o evento e não envia qualquer intenção de execução.

## Contrato da futura execução

A feature flag `CORPORATE_COMPLEX_EVENTS_EXECUTION_ENABLED` é `false` por padrão.
O contrato de intenção avalia, nesta ordem, revisão humana finalizada, plano
econômico completo e feature flag. A identidade combina evento, carteira,
identidade econômica, revisão e plano em uma chave SHA-256 determinística.

Os estados possíveis são `BLOCKED_EVENT_NOT_REVIEWED`, `BLOCKED_PLAN`,
`BLOCKED_FEATURE_DISABLED` e `READY`. Todos retornam `writable=false`, inclusive
`READY`: ainda não existe porta de escrita, ledger ou mutação de posições. Esse
contrato fixa os gates e a identidade idempotente para o próximo bloco sem
ampliar a superfície operacional atual.
