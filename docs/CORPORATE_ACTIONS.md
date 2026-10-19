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

## Auditoria do runtime publicado - 18/10/2026

Esta validacao posterior substitui o retrato de publicacao de 16/10 acima para o estado operacional. O Compose sig-v2 esta ativo: backend, PostgreSQL e Redis healthy; frontend e Cloudflare Tunnel em execucao. Backend /health=200, Alembic 20261017_fixed_income_contracts (head). Nenhuma sincronizacao, reconciliacao nem escrita de dados financeiros foi feita.

### Cobertura funcional verificada

- O OpenAPI publicado expoe as rotas de lifecycle do ativo e de fracoes pendentes. GETs sem sessao responderam 401, confirmando autenticacao; a jornada autenticada nao foi exercitada nesta auditoria.
- O leitor canonico exclui eventos novos sem MATCHED, sem is_canonical ou com requires_review=true; a compatibilidade legacy segue separada. A projecao nao altera o ledger.
- Testes backend focados em elegibilidade, leitor, snapshots, lifecycle, reconciliacao e migration: 80 passaram. Testes de UI do detalhe do ativo e painel de fracoes: 6 passaram.
- O catalogo runtime tem 125 eventos: 121 UNRECONCILED, 3 CONFLICT e 1 MATCHED elegivel. Dois eventos B3 de NIKE34 permanecem sem effective_date. Ha tres conflitos em datas com posicao registrada: AMOB3 (evento 12, 28/05/2025) e KLBN11 (eventos 81/82, 17-18/12/2025). Eles ficam fora da projecao por politica; seus efeitos historicos nao estao reconciliados.
- O scheduler nao sincroniza eventos corporativos de forma recorrente. A coleta ocorre pelo bootstrap explicitamente autorizado; a politica evita escrita externa implicita em runtime. Os registros mais recentes no catalogo sao de 16/10 para B3 e 22/09 para BRAPI/Yahoo, portanto a atualidade de provedores precisa de uma auditoria/execucao escopada antes de qualquer conclusao de cobertura completa.

### Limites e proximos passos

/ready=503 indica incompatibilidade da identidade persistida de certificacao nos campos commit, dataset e revisao Alembic. O bloqueio e do contrato de readiness para dados reais; backend e interface seguem em funcionamento para a stack atual. Nenhuma certificacao foi renovada neste bloco.

A Issue #370 continua aberta pela falta de evidencia externa de liquidacao de KLBN11. Nao converter conflitos em MATCHED nem corrigir fatores/datas por suposicao. Proxima validacao funcional: executar os GETs de lifecycle com uma sessao de teste autorizada e revisar os tres conflitos junto de extrato de custodia/corretora; completar a lacuna de data efetiva de NIKE34 com calendario oficial antes de considerar esse evento elegivel.
## Significado e inventario de UNRECONCILED - 18/10/2026

UNRECONCILED e um estado de reconciliacao do fato, nao uma indicacao de que o evento nao esteja ligado ao ativo global nem de que seja falso. Os registros do catalogo sao associados por asset_id; a projecao financeira atual tambem exige portfolio_id nulo para tratar uma acao como global. Para eventos de provedores, o leitor so permite projeção quando a linha e canonical, reconciliation_status=MATCHED e requires_review=false. Portanto, hoje os 120 eventos globais UNRECONCILED estao persistidos mas nao afetam nenhuma carteira.

### Composicao do catalogo

| Origem | Registros | Ativos | Tipos e detalhe |
|---|---:|---:|---|
| B3 | 2 | NIKE34 | 1 desdobramento de 08/02/2021 e 1 grupamento de 09/10/2026; ambos sem effective_date. O adaptador preserva lastDatePrior/record_date e aguarda a sessao efetiva oficial. |
| BRAPI | 46 | 17 | 28 bonificacoes, 10 desdobramentos e 8 grupamentos; datas de 1986 a 2026. |
| Yahoo | 72 | 17 | 67 desdobramentos e 5 grupamentos; datas de 2000 a 2025. Fallback/ suplemento, nao autoridade para substituir B3 coberta. |
| ticker_resolution | 1 | PETZ3 | Troca PETZ3 para AUAU3 em 05/01/2026; possui asset_id, mas tambem portfolio_id e nao e acao global de quantidade. |

No catalogo inteiro, 124/125 linhas tem portfolio_id nulo e todas tem asset_id. A excecao e o registro ticker_resolution acima, que esta no escopo de uma carteira. A linha esta marcada APLICADO no subsistema de troca de ticker, mas continua UNRECONCILED/requires_review e nao entra no projetor global de splits/bonificacoes. A consulta encontrou zero transacoes com o marcador sintetico desse evento.

Os dois registros B3 tem review_reason explicito pela data efetiva pendente. Os 118 registros BRAPI/Yahoo nao trazem motivo de revisao salvo; todos foram inseridos no estado default UNRECONCILED/requires_review. Isso e uma lacuna de classificacao/auditoria, nao evidencia de que cada evento seja incorreto. is_canonical=true por si so nao libera a projecao.

### Comparacao entre fontes e impacto no ledger atual

O CLI read-only de candidatos exatos retornou zero grupos e zero escritas. Sua regra exige mesmo ticker, tipo, effective_date e fator entre pelo menos duas fontes. A consulta de inventario encontrou 10 pares BRAPI/Yahoo com tipo e fator iguais, mas data divergente em 1 a 3 dias: BBAS3, GOAU4 (dois eventos), KLBN11, PETR4, RANI3, TAEE11, VULC3 (dois eventos) e WEGE3. Sao candidatos de investigacao; diferencas de data podem refletir record/ex-date versus sessao efetiva e nao autorizam combinar ou deslocar fatos.

Usando somente transactions persistidas e effective_date disponivel, nenhum dos 118 eventos BRAPI/Yahoo UNRECONCILED coincidiu com quantidade positiva no ledger de uma carteira na data do evento. Os dois eventos B3 sem effective_date nao podem ser avaliados por esse criterio. Em contraste, os tres registros CONFLICT de AMOB3 e KLBN11 ja identificados na auditoria anterior coincidem com datas com posicao e permanecem fora da projecao.

### Alinhamento necessario

A arquitetura pretendida e global: um fato corporativo canonico do ativo deve ser projetado sobre cada ledger que possuia quantidade elegivel na data efetiva, sem mutar transacoes historicas. O estado de reconciliacao atual exige MATCHED inclusive para uma linha isolada de fonte autorizada, e a descoberta de candidatos depende de duas fontes com data identica. Isso deixa fatos potencialmente validos bloqueados e nao representa sozinho a autoridade por provedor.

O proximo bloco deve classificar elegibilidade por fonte e tipo: B3 oficial pode fundamentar o fato quando data efetiva, fator e payload estao completos; BRAPI so complementa fatos fora da cobertura B3; Yahoo continua fallback explicitamente identificado onde nao ha cobertura oficial. Duplicatas e divergencias devem continuar sem dupla aplicacao, com proveniencia preservada. Nenhuma promocao em lote de UNRECONCILED para MATCHED e autorizada por este inventario.

## Auditoria do conector B3 - 18/10/2026

Foi feita uma consulta read-only pelo `B3ListedCompaniesClient` para os 21 tickers
de eventos globais cujo ativo no catalogo e ACAO ou BDR. A B3 respondeu para os
21 emissores; 19 payloads passaram pela normalizacao atual e dois falharam por
fator invalido (BBDC3 e RANI3). A consulta e a comparacao fizeram zero escritas
no banco.

Esta auditoria encontrou dois defeitos que impedem executar o seed atual com
`--execute`:

1. O endpoint de emissor retorna acoes de varias classes, identificadas por
   `isinCode`. `corporate_actions()` apenas verifica que o ISIN esperado aparece
   em algum item, mas `normalize_b3_corporate_actions()` inclui todos os itens.
   Exemplo: ALUP11 retornou seis linhas, das quais somente duas tinham o ISIN
   do ativo. Isso pode vincular acoes de outra classe ao ticker consultado.
2. A coluna B3 e `% / Split Factor`. A normalizacao atual grava o valor bruto de
   `factor` como `quantity_factor`. A comparacao com eventos existentes mostra
   que bonificacoes e desdobramentos precisam ser convertidos de percentual para
   multiplicador (`1 + percentual / 100`); grupamentos ja chegam como fator
   multiplicador. Exemplos observados: bonificacao de 4% corresponde a 1,04;
   desdobramento de 70% corresponde a 1,70; grupamento de 0,02 permanece 0,02.
   As paginas B3 mostram a coluna e identificam as acoes por classe/ISIN:
   [exemplo de acoes corporativas B3](https://sistemaswebb3-listados.b3.com.br/listedCompaniesPage/main/1228/BNBR/corporate-actions?language=en-US).

A comparacao somente para investigacao encontrou corroboracao B3 de eventos
existentes, incluindo AMOB3 (record date 28/05/2025, grupamento 0,02) e KLBN11
(bonificacao de 1% em 17/12/2025). Essas respostas confirmam fatos do emissor,
mas nao resolvem por si so data efetiva, fracao/liquidacao ou a elegibilidade de
cada carteira. AMOB3 IDs 12/13 e KLBN11 IDs 81/82 mantem seus estados atuais; o
conector nao gravou, promoveu, ocultou nem aplicou nenhum evento.

### Correcao local do normalizador - 18/10/2026

O normalizador agora converte bonificacao/desdobramento percentual em
multiplicador, conserva grupamento como multiplicador, restringe eventos ao
ISIN atual do ativo e falha fechado quando ha classe ambigua ou tipo nao
suportado. Subscricoes ficam identificadas como direito sem efeito automatico
na quantidade. Um novo dry-run foi feito para os mesmos 21 tickers: 17 payloads
passaram; BBDC3 e RANI3 continuam bloqueados por fator invalido; PETZ3 e SANB11
por acoes corporativas nao suportadas (`INCORPORACAO` e `CIS RED CAP`). Os testes
focados passaram (22/22) numa copia isolada do codigo. Nenhuma escrita foi feita
no banco e a imagem/runtime ainda precisa receber esta alteracao.

Antes de nova coleta ampla com escrita, tratar manualmente os quatro payloads
bloqueados. Naquele dry-run, os dois registros B3 de NIKE34 ainda precisavam de
plano de reconciliacao e calendario; o evento 164 tinha fator persistido 900,
embora o fator de quantidade normalizado pela B3 seja 10. O evento 165 foi
tratado na secao seguinte. Gerar backup consistente e validar por ledger e
politica de fracao antes de qualquer promocao ou projecao. O estado
`UNRECONCILED` continua significando fato pendente de reconciliacao, mesmo
quando ha evidencia B3 associada ao ativo.

### Aplicacao do grupamento B3 NIKE34 - 18/10/2026

O evento B3 165 foi reconciliado como canonico apos dry-run e backup v3
consistente. A B3 informa fator 0,2 e `lastDatePrior=2026-10-09`; o calendario
oficial B3 marca 12/10 como feriado, portanto a primeira sessao efetiva e
13/10/2026. O registro ficou `MATCHED`, `effective_date=2026-10-13` e politica
`PENDING_SETTLEMENT`. A evidencia oficial foi persistida sem preco de liquidacao
ou tratamento de caixa.

No preflight global, somente a carteira 15 tinha posicao elegivel: 6 NIKE34 em
3 compras anteriores ao record date. A projecao agora resulta em 1 BDR e fracao
pendente de 0,2; nenhum caixa ou resultado realizado foi criado. A execucao
invalidou 4 snapshots, reconstruiu 520 e invalidou o cache de rentabilidade de
uma carteira. A leitura read-only posterior confirmou que o evento entrou no
projetor e que a fracao de 0,2 permanece pendente.

O backup anterior a escrita e
`artifacts/pre-prod-rebuild/20261018-nike34-event165-pre`, contrato
`pre-prod-backup.v3`, snapshot consistente, SHA-256
`32ea9db5f816beeab5c83386277dfe7493f4c19d26aa5cd61066078354b92711`, associado
ao commit de runtime `8391474917684caa4e92f30d8b7c00cdb7ac5a28`. Fontes do
calendario: [B3 2026](https://www.b3.com.br/data/files/20/57/01/AA/06A1F910ADC36BE9AC094EA8/OC%20041-2026-VNC%20ERRATA%20-%20CALENDARIO%20DE%20FERIADOS%20EM%202026_PT.pdf)
e [calendario B3 2021](https://www.b3.com.br/pt_br/solucoes/plataformas/puma-trading-system/para-participantes-e-traders/calendario-de-negociacao/feriados/).

O outro registro B3, evento 164 (desdobramento de 2021), segue `UNRECONCILED` e
fora da projecao. O fator persistido 900 ainda precisa de reparo para o
multiplicador oficial 10; nao havia transacoes NIKE34 ate 09/02/2021 em nenhuma
carteira. Os estados de AMOB3 e KLBN11 nao foram alterados.
