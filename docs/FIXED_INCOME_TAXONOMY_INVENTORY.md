# Inventario da taxonomia de Renda Fixa — Issue #355

Atualizado em 17/10/2026. Escopo: leitura estatica do checkout local
`stable-15jun` em `5c4ad3906475316294196a826ff140cb3e4bf950`, complementada
por auditoria DB-only read-only na stack sintetica `sgi-usertest`.

## Estado observado

### Lifecycle e schema

- `transactions` e o ledger canonico para aplicacoes e resgates. O ORM em
  `backend/app/models/transaction.py` armazena portfolio, ticker, classe,
  operacao, quantidade, preco, taxas, data, moeda e `notes`; nao ha campos
  tipados para produto, emissor, indexador, taxa, liquidez ou vencimento.
- `TransactionCreate` e `TransactionUpdate` preservam esse contrato generico.
  O writer compartilhado (`transaction_write_service.py`) atende escrita HTTP,
  CSV e chamadas de certificacao.
- `assets` e um catalogo global por ticker/classe, nao uma entidade de contrato
  de aplicacao. O writer cria um Asset generico quando necessario.
- A migration `20260903_drop_fixed_income` removeu `fixed_income_investments`
  depois de exigir tabela vazia; o downgrade e explicitamente irreversivel.
  Nao recriar essa tabela nem seu antigo enum como fonte de posicao.

### API, UI e importacao

- O formulario `AddTransactionModal.tsx` pede indexador, taxa, vencimento,
  liquidez diaria e emissor para Renda Fixa. Nao oferece taxonomia de produto.
- Esses valores sao concatenados em texto livre de `notes`, junto com o nome do
  ativo e notas do usuario. O backend nao os valida como contrato estruturado.
- A API de transacoes aceita `notes` como texto opcional e o endpoint de edicao
  substitui esse campo diretamente quando enviado.
- O CSV canonico tem `notes`, mas nao colunas tipadas de produto/contrato. O
  importador encaminha as linhas ao mesmo writer de transacoes.

### Valuation e projecoes

- `fixed_income_valuation_service.py` le as transacoes da carteira e interpreta
  `Indexador:`, taxa e `Vencimento:` por regex em `notes`.
- As aplicacoes sao reconstruidas de compras e reducoes a partir de resgates;
  principal aplicado e `quantity * price + fees`. O agrupamento usa ticker,
  indexador, taxa, vencimento e fonte qualificada do benchmark, nao identidade
  estavel de contrato.
- Resgates com metadados completos tentam casar a chave composta; sem chave,
  usam ticker. Variacoes textuais das notas podem, portanto, mudar agrupamento
  ou associacao do resgate.
- Posicoes, resumo, snapshots e TWR consomem esses projetores. Metadados novos
  nao devem introduzir saldo, quantidade liquida, valor atual ou resultado
  persistidos como segunda autoridade.
- `fixed_income_contract_audit_service.py` e a CLI
  `audit_fixed_income_contracts.py` oferecem auditoria DB-only da cobertura de
  metadados. A CLI foi executada em modo somente leitura na stack `sgi-usertest`
  em 17/10/2026, apos validar identidade `ENVIRONMENT=testing`, branch
  `stable-15jun`, SHA base `5c4ad3906475316294196a826ff140cb3e4bf950`, dataset
  real nao configurado e Alembic em `20261016_corp_ev_effective_date`.
  Resultado: zero transacoes, compras ou resgates; nao ha contratos sinteticos
  nesta base para medir cobertura.

## Evidencia anterior e limite

O comentario remoto da #355 registra auditoria de 11/09/2026 numa baseline
anterior: 29 transacoes, 27 metadados suficientes e 2 incompletos; aponta
payloads textuais diferentes para aplicacoes semanticamente proximas e
representacoes diferentes de principal em `quantity`/`price`. Esses numeros
nao foram reproduzidos neste checkout e nao descrevem necessariamente o banco
atual. Servem como alerta de compatibilidade, nao como inventario corrente.

## Proposta tecnica preliminar

Esta proposta traduz a Issue em um desenho para revisao; ainda nao e decisao de
schema nem autorizacao de migration.

- `product_type` candidato: `CDB`, `RDB`, `LCI`, `LCA`, `LC`, `LIG`, `CRI`,
  `CRA`, `DEBENTURE`, `DEBENTURE_INCENTIVADA`, `LETRA_FINANCEIRA` e `OUTRO`.
- Indexador continua campo separado (`CDI`, `SELIC`, `IPCA_PLUS`,
  `PREFIXADO`, `IGPM_PLUS`); valor e base da taxa tambem precisam ser
  independentes para distinguir percentual do indexador de percentual anual.
- Candidato a `fixed_income_contracts`: identidade e metadados do contrato,
  escopados por `portfolio_id`, com nome de exibicao, tipo, emissor,
  indexador, taxa/base, liquidez/carencia, vencimento, moeda e metadados de
  origem quando houver evidencia. `tax_exempt` nao deve ser inferido somente
  de `product_type` nem tratado como aconselhamento/regra tributaria geral.
- Candidato a ligacao: campo nullable `transactions.fixed_income_contract_id`
  para permitir rollout compativel e relacao 1:N de aplicacoes/resgates ao
  contrato. Operacoes antigas sem ligacao continuam legiveis durante a
  transicao por `notes`; novos writes estruturados devem passar pelo writer
  canonico. Confirmar se uma relacao polimorfica por classe cabe nos contratos
  existentes antes de escolher o nome e a FK final.
- A politica de exclusao do contrato segue em aberto. Uma FK nao pode apagar
  transacoes em cascata; definir se contratos referenciados ficam restritos a
  exclusao ou se a desvinculacao exige acao explicita e auditavel.
- A entidade de contrato nao armazena principal, quantidade liquida, saldo,
  valor atual ou resultado. Estes seguem derivados exclusivamente de
  `transactions` e dos benchmarks persistidos usados pelo valuation.

Sequencia proposta: confirmar taxonomia/semantica; definir DTOs e formato CSV
retrocompativel; adicionar schema apenas de metadados e ligacao nullable;
atualizar writer/UI/leitores com fallback explicito; auditar cobertura em banco
sintetico; somente depois preparar backfill revisado, idempotente e reversivel.
O backfill nao deve ser parte da migration estrutural nem deduzir identidade de
contrato usando apenas ticker ou texto bruto.

## Decisao corrente de produto - 18/10/2026

Esta decisao supersede a proposta preliminar acima para o preenchimento fiscal
e a identidade visivel do titulo:

- `tax_exempt` e derivado de `product_type` no schema da API e na UI; nao e um
  campo editavel nem uma informacao solicitada ao usuario;
- CDB, RDB, LC, debenture comum, Letra Financeira e Outro seguem o tratamento
  tributavel padrao. LCI, LCA, LIG, CRI, CRA e debenture incentivada sao
  classificados como isentos, sujeitos aos requisitos da emissao e do titular;
- a classificacao padrao nao prepara nem transmite declaracao de IRPF e nao gera
  DARF. A retencao aplicavel a produtos tributaveis e feita pela fonte pagadora;
- a tela usa um campo para nome completo do titulo, incluindo o emissor; nao
  solicita emissor separado. O metadado legado `issuer` permanece no modelo e
  em importacoes antigas, mas novos contratos da tela o deixam nulo;
- liquidez diaria oculta vencimento e carencia e grava `grace_period_end=null`;
- contratos antigos podem ser reaproveitados sem campo de emissor quando o nome
  informado contem o emissor legado. Nomes que nao identificam o emissor nao
  sao fundidos automaticamente.

As regras fiscais implementadas e fontes oficiais estao em
`docs/TOOLS_CALCULATORS.md`; essa classificacao e uma regra padrao do produto,
nao substitui o informe financeiro nem a verificacao do enquadramento legal.

## Revisao dos caminhos de escrita — 17/10/2026

A verificacao das chamadas existentes detalhou os pontos que uma ligacao
tipada precisara cobrir:

- criacao HTTP e importacao CSV chamam o writer canonico; certificacao sintetica
  tambem possui caminhos de seed com construcao direta de `Transaction`;
- `PATCH /transactions/{id}` atualiza o ORM diretamente. Se aceitar contrato,
  precisa validar ownership e classe; ao converter uma transacao para outra
  classe, nao pode manter uma FK de Renda Fixa incompatível;
- `ticker_change_processor.py` cria transacoes tecnicas diretamente. A nova FK
  nullable deve permanecer sem efeito para esses eventos nao contratuais;
- a migration e o ORM devem permitir registros preexistentes sem contrato. A
  leitura deve manter fallback legado explicito ate cobertura comprovada;
- auditoria/testes da implementacao devem cobrir contrato de outra carteira,
  classe incompatível, criacao/edicao, CSV legado sem campo, seed sintetico,
  eventos tecnicos e associacao de resgates ao mesmo contrato.

Conclusao desta revisao: a FK nullable e tecnicamente compatível como formato
de rollout, desde que a associacao seja validada no service/API e que leituras
legadas continuem suportadas. Isso ainda nao resolve a identidade dos contratos
existentes nem justifica executar backfill. A implementacao depende de massa
sintetica de Renda Fixa e de um ciclo de migration/validacao em banco
descartavel.

## Decisoes para a proxima etapa

1. Definir taxonomia de `product_type` separada de indexador, taxa, unidade,
   liquidez, carencia, vencimento, emissor e isencao tributaria.
2. Especificar identidade de contrato e relacao 1:N entre contrato e
   transacoes de aplicacao/resgate. Nao usar `notes` como chave persistente.
3. Manter `transactions` como unica fonte do lifecycle. Metadados contratuais
   podem descrever instrumentos, mas nunca guardar posicao ou valuation.
4. Desenhar compatibilidade para API, formulario, edicao, CSV, auditoria,
   valuation, snapshots/TWR, resumo e IRPF antes de qualquer migration.
5. Carregar cenarios sinteticos de Renda Fixa em fluxo controlado e reexecutar a
   auditoria em banco cuja identidade/massa estejam comprovadas. Nao usar a
   auditoria antiga para backfill nem deduzir tipo automaticamente.

Este bloco conclui o inventario, a proposta preliminar e a revisao estatica dos
caminhos de escrita; nao fecha os campos obrigatorios, a politica de ligacao
dos dados antigos nem autoriza migration, backfill ou alteracao financeira.


## Estado de implementacao - 17/10/2026

A etapa seguinte foi iniciada localmente: modelo `FixedIncomeContract`, endpoints
GET/POST por carteira, campo nullable `transactions.fixed_income_contract_id`,
validacao de ownership/classe no writer canonico e migration aditiva
`20261017_fixed_income_contracts`. Foram adicionados testes unitarios de criacao,
listagem, ownership e semantica da taxa. Nao ha backfill e nenhum ledger foi
alterado.

A validacao nao foi concluida. O pytest local nao carregou porque o Python host
nao tem `pydantic`; a tentativa de rebuild da stack `sgi-usertest` terminou em
BuildKit `error reading from server: EOF`, e o daemon deixou de responder as
consultas seguintes. Portanto, nao se confirmou teste, migration, API ou troca da imagem
em runtime. O proximo passo operacional e restaurar/confirmar o Docker, entao
rodar os testes focados e aplicar a migration somente em banco descartavel. A
proposta anterior de compatibilidade continua sujeita a essa validacao; nao
tratar o codigo atual como entregue ou certificado.


## Validacao apos recuperacao do Docker - 17/10/2026

Esta atualizacao substitui o estado de bloqueio operacional registrado acima.
O backend e frontend foram reconstruidos em `sgi-usertest`; a migration foi
aplicada ate `head`, os 18 testes focados passaram sem avisos ORM, a API consta
na OpenAPI, `/health=200` e o frontend respondeu 200. `/ready=503` permanece
esperado para a identidade `testing` sem dataset real ou certificacao. Um teste
PostgreSQL transacional com rollback rejeitou vinculo entre carteiras e deixou
contagens zero para carteiras, transacoes e contratos. Digests estao em
`docs/USER_TEST_STACK.md`. A API ainda nao foi integrada ao formulario nem ao
CSV; nao houve backfill e nenhum dado permaneceu gravado pelo exercicio.


## Integracao transacional do formulario — 17/10/2026

`AddTransactionModal` agora lista contratos da carteira e permite criar um contrato estruturado dentro da gravacao de aplicacao/resgate. Contrato e lancamento sao persistidos no mesmo unit of work. Na edicao, o vinculo existente e preservado; tambem e possivel converter um lancamento legado sem vinculo para contrato estruturado, enquanto a opcao legado mantem o registro sem associacao. Valores originais de quantidade e preco sao preservados na edicao de Renda Fixa.

A importacao CSV antiga permanece compativel e nao cria/associa contratos nem tenta deduzir identidade de produto. O CSV ainda nao transporta os novos metadados. Quatro testes backend cobrem criacao atomica, classe nao permitida, edicao e importacao legada; 16 testes focados de frontend e typecheck passaram. Nenhum registro foi gravado no banco da stack de testes.


## Contratos no CSV - 18/10/2026

Colunas opcionais: `fixed_income_contract_key`, `fixed_income_product_type`, `fixed_income_display_name`, `fixed_income_issuer`, `fixed_income_indexer`, `fixed_income_rate_value`, `fixed_income_rate_unit`, `fixed_income_maturity_date`, `fixed_income_liquidity_type`, `fixed_income_grace_period_end`, `fixed_income_tax_exempt` e `fixed_income_currency`. Tipo de produto, indexador, unidade de taxa e liquidez usam os valores canonicos das schemas da API; datas aceitam os formatos de data ja reconhecidos pelo importador. Taxa e unidade precisam respeitar o par e indexador definido no contrato.

## Hierarquia do formulario e limite tributario - 18/10/2026

No cadastro de contrato, `product_type` aparece antes do indexador porque a
classificacao do instrumento deve orientar a coleta das demais condicoes. Para
LCI, LCA, LIG, CRI, CRA e debenture incentivada, a interface sugere isencao
tributaria usual; para outros produtos sem regra geral segura, mantem o estado
`nao informado`. A sugestao e editavel e nao substitui confirmacao da emissao,
do titular ou da legislacao aplicavel. Isso e apenas metadado do contrato: nao
representa calculo de imposto, aconselhamento tributario ou alteracao do motor
de IRPF. O indexador, a taxa e a unidade continuam campos independentes e
validados pelo contrato canonico.

## Associacao transparente por equivalencia - 18/10/2026

O formulario nao expoe ao usuario a escolha de um registro interno de contrato.
Ao gravar novos termos, o writer procura contrato equivalente na mesma
carteira, comparando nome (sem diferenca de caixa), produto, emissor,
indexador, taxa/unidade, vencimento, liquidez, carencia, tributacao e moeda;
se encontrar, vincula a nova transacao ao registro existente. Diferenca em
qualquer termo cria outro contrato, sem fundir instrumentos apenas por ticker.
Atalho de Renda Fixa no resumo carrega os termos apenas quando nome/codigo
corresponde a exatamente um contrato da carteira. Tesouro permanece
identificado pelo simbolo canonico do catalogo, com vencimento, indexador, taxa
e PU obtidos do prefill/cotacao persistida conforme disponibilidade. A
transacao continua sendo o unico ledger; contratos sao metadados.

A chave e unica somente dentro do arquivo. Repetir a mesma chave com termos identicos permite varias aplicacoes ligadas ao mesmo contrato; termos divergentes bloqueiam o arquivo. Contrato sem chave, chave sem termos minimos, ou metadados em classe diferente de `RENDA_FIXA` sao rejeitados no dry-run. A grava??o usa o writer can?nico e a transacao do lote; erros fazem rollback completo. O export autenticado gera chaves sequenciais do arquivo, nunca ids do banco, e inclui os termos nas linhas ligadas. O CSV antigo de nove colunas permanece valido e nao associa metadados a partir de `notes` ou ticker.

## Estado corrente e associacao automatica - 18/10/2026

Os snapshots e propostas acima descrevem a etapa de inventario original. O
checkout corrente ja tem `fixed_income_contracts`, FK nullable em `transactions`,
API portfolio-scoped, metadados tipados no formulario e CSV estruturado com
chave local ao arquivo. O formulario nao apresenta seletor de ID de contrato:
o writer reutiliza os termos equivalentes dentro da carteira; ticker sozinho
nao e criterio. `transactions` continua sendo o unico ledger e nenhum backfill
foi autorizado ou executado.

Nomes de exibicao e emissor agora colapsam espacos consecutivos ao validar o
payload; comparacao de equivalencia trata caixa do nome/emissor como nao
significativa. Os demais termos permanecem exatos e portfolio-scoped. Testes
focados verificam equivalencia normalizada, divergencia de taxa e isolamento
entre carteiras. Em 18/10/2026, 13 testes do servico passaram em SQLite em
memoria. A base persistente de `sgi-usertest` segue com zero transacoes e zero
contratos; digests estao em `docs/USER_TEST_STACK.md`.

Pendencias verificaveis: Vitest de prefill sem resultado por travamento do
runner; validacao visual depende de browser integrado disponivel. A Issue #355
no GitHub ainda lista seletor explicito como criterio; deve ser alinhada ao
fluxo transparente antes de qualquer encerramento da Issue. Nenhum dado real foi
usado neste bloco.

## Verificação seguinte — 18/10/2026

O teste de interface focado foi retomado e concluiu com 15/15 testes,
incluindo reconhecimento automático de contrato único no prefill do Resumo e
preservação de vínculo durante edição. O banco persistente principal não foi
escrito. A validação visual segue pendente porque não havia navegador conectado
na sessão. O trecho acima sobre a base `sgi-usertest` é histórico; o único
runtime de testes com usuários é agora `sig-v2` pelo Cloudflare Tunnel, conforme
`docs/USER_VALIDATION_RUNBOOK.md`.

A Issue #355 ainda contém o critério antigo de seletor explícito. O fluxo
implementado associa por equivalência de termos e não expõe esse seletor. Manter
a Issue aberta até alinhar o critério remoto com essa decisão de produto.
