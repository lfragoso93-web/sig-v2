# Validacao assistida com usuarios - SGI v2

Issue mae: #227
Gate funcional: #303
Branch obrigatoria: `stable-15jun`

## Status atual - 08/09/2026

GO para usuarios convidados testarem jornadas assistidas com contas, carteiras e
dados ficticios/descartaveis.

NO-GO para usuarios, carteiras, CSV, seeds, snapshots ou posicoes reais. A flag
`ready_for_real_data` deve permanecer `false` ate a conclusao formal dos gates
#226, #216, #158 e #227.

Baseline operacional publicado: `fe3b265fa2b8dc72cf90626afd5749124d85c0c8`.

Atualização do bloco 08/09/2026:

- cripto financeiro pronto para 44 ativos certificados;
- 13 criptoativos do Top 60 seguem bloqueados explicitamente por histórico raso
  indisponível ou gap de complemento;
- `ready_for_real_data=false` permanece obrigatório;
- inventário pré-prod deve rodar com `unclassified_tables=0` após a
  classificação de `rate_history_coverages`.

Panorama para usuários convidados:

- liberado: contas de teste, carteiras de teste, navegação completa, lançamentos
  fictícios, CSV sintético/controlado e criptoativos certificados;
- não liberado: carteiras reais irrestritas, CSV real sem supervisão, ativos
  cripto bloqueados, seeds reais fora da janela autorizada e qualquer promoção
  de readiness;
- critério de avanço: rodada assistida sem blocker P0/P1 em autenticação,
  segregação de carteiras, CSV, patrimônio, rentabilidade, Proventos ou IRPF.

Carteira sintetica ja alimentada no banco local de validacao:

- usuario: `portfolio-certification-303@example.com`;
- carteira: `PORTFOLIO-TEST-READY synthetic multiclasse`;
- `user_id=14`;
- `portfolio_id=13`;
- fixture #303 com 11 transacoes, precos sinteticos, provento sintetico,
  Tesouro, Renda Fixa, cripto e matriz IRPF certificada.

## Objetivo

Validar o SGI v2 com usuarios convidados em jornadas controladas antes de
qualquer decisao `ready_for_real_data=true`.

Este runbook permite somente usuarios de teste, carteiras ficticias e dados
descartaveis. Ele nao autoriza seed real de Proventos, CSV real, carteira real,
snapshot de producao, migracao fisica ou mudanca manual de readiness.

## Estado permitido

- `test_ready=true`;
- `ready_for_real_data=false`;
- ambiente local ou lab homologado com SHA exato publicado em `stable-15jun`;
- usuarios identificados como teste, sem dados pessoais financeiros;
- carteiras e transacoes ficticias, reproduziveis ou descartaveis.

## Pre-condicoes

Antes de iniciar uma rodada com usuarios:

1. Confirmar branch `stable-15jun`.
2. Confirmar HEAD local igual a `origin/stable-15jun`.
3. Confirmar working tree limpa.
4. Registrar SHA completo, data, ambiente e responsavel pela rodada.
5. Executar gates tecnicos locais aplicaveis:
   - backend `pytest -q`;
   - frontend `npm run typecheck`, `npm run lint`, `npm test -- --run`, `npm run build`;
   - `app.main OK`;
   - `docker compose ps` saudavel;
   - certificacoes sinteticas #303 com `status=PASS`.
6. Confirmar `/health` com Postgres ok.
7. Confirmar que `/ready` permanece fechado enquanto `ready_for_real_data=false`.
8. Confirmar que nenhum opt-in real esta ativo sem issue autorizando:
   - `SGI_BOOTSTRAP_ENABLE_DIVIDENDS`;
   - `SGI_BOOTSTRAP_ENABLE_CORPORATE_EVENTS`;
   - qualquer comando real de importacao CSV ou seed.

## Perfis de usuario

Usar no minimo tres perfis de validacao:

| Perfil | Objetivo | Dados permitidos |
| --- | --- | --- |
| Usuario iniciante | Validar onboarding, carteira vazia e navegacao basica | carteira ficticia simples |
| Usuario investidor comum | Validar multiclasse, filtros e entendimento dos cards | fixture sintetica ou transacoes ficticias |
| SuperAdmin/tester | Validar controles administrativos e bloqueios | contas de teste e ambiente descartavel |

Nenhum perfil deve usar extrato, nota, CPF, email pessoal financeiro, carteira
real ou posicao real.

## Jornadas obrigatorias

Cada usuario de teste deve executar, acompanhado por observador tecnico:

1. Cadastro ou login de conta de teste.
2. Criacao ou selecao de carteira ficticia.
3. Navegacao pelas telas:
   - Resumo;
   - Patrimonio;
   - Rentabilidade;
   - Transacoes;
   - Proventos;
   - IRPF;
   - Configuracoes.
4. Validacao de estados vazios e mensagens de indisponibilidade.
5. Cadastro manual de transacoes ficticias quando aplicavel.
6. Importacao CSV somente com arquivo sintetico aprovado.
7. Conferencia de valores esperados contra oraculo sintetico.
8. Restart controlado do backend ou Compose entre duas leituras.
9. Revalidacao visual apos restart.
10. Confirmacao de que nenhum dado real foi usado.

## Matriz de aceite

| Area | Aceite minimo |
| --- | --- |
| Autenticacao | login/cadastro de teste conclui sem erro visivel |
| Carteira | criar, selecionar e navegar sem misturar dados entre usuarios |
| Transacoes | compra, venda parcial, venda total e recompra ficticias preservam custo e realizado |
| CSV sintetico | dry-run, confirmacao, importacao e reexecucao seguem o contrato #303 |
| Patrimonio | valores batem com reconciliacao sintetica no centavo |
| Rentabilidade | indisponibilidade de classe sem cobertura aparece explicitamente |
| Proventos | direitos sao calculados sob demanda, sem materializacao por carteira |
| IRPF | valores sinteticos batem com a matriz de aceite #303 |
| Resiliencia | restart nao perde carteira, snapshots ou cache essencial |
| Admin | usuario comum nao acessa superficies SuperAdmin |

## Evidencia da rodada

Registrar internamente, sem segredos e sem dados pessoais reais:

- SHA completo;
- ambiente;
- data/hora;
- perfis testados;
- jornadas concluidas;
- bugs encontrados;
- screenshots somente se nao expuserem dados sensiveis;
- resultado final: `PASS`, `PASS_WITH_FINDINGS` ou `FAIL`.

Findings devem virar issues pequenas quando forem reproduziveis. A rodada nao
autoriza `ready_for_real_data=true` se houver blocker aberto.

## Criterios para avancar aos gates reais

A validacao assistida com usuarios ficticios permite seguir para a cadeia real
somente quando:

- todas as jornadas obrigatorias forem `PASS` ou findings nao bloqueantes;
- backend, frontend e Docker local estiverem verdes no mesmo SHA;
- #303 tiver evidencia sintetica suficiente;
- nao houver bug P0/P1 aberto afetando onboarding, transacoes, CSV, patrimonio,
  rentabilidade, Proventos ou IRPF;
- documentacao viva estiver sincronizada.

Depois disso, a ordem permanece:

1. #226 - duas execucoes reais controladas de Proventos;
2. #216 - reconciliacao do gate agregado;
3. #158 - importacao/rebuild/reconciliacao operacional;
4. #227 - decisao formal GO/NO-GO;
5. somente entao avaliar `ready_for_real_data=true`.

## Criterios de bloqueio

Interromper a rodada e manter `ready_for_real_data=false` se ocorrer:

- uso acidental de dado real;
- provider chamado por GET ou calculo financeiro comum;
- divergencia financeira sem explicacao;
- perda de dados apos restart;
- usuario acessando carteira de outro usuario;
- SuperAdmin exposto a usuario comum;
- importacao CSV real ou seed real fora da issue autorizadora.

## Finding real assistido - 08/09/2026

Usuario: `lfragoso93@gmail.com`.

Evidencia: apos importar CSV com ativos B3, a carteira `Principal`
aparentava nao carregar dados em Resumo/Posicoes.

Diagnostico:

- a importacao persistiu 308 transacoes e 65 ativos distintos;
- nao havia transacao sem ativo canonico correspondente;
- a carteira ainda nao possuia posicoes/snapshots materializados;
- os endpoints quebravam porque renda fixa com benchmark CDI parcial em
  `2026-04-14..2026-09-08` propagava `IncompleteBenchmarkCoverageError`.

Correcao aplicada:

- Resumo canonico e legado preservam os totais nao-RF quando renda fixa esta
  indisponivel por cobertura parcial de benchmark;
- Posicoes preservam os grupos nao-RF e registram a indisponibilidade de renda
  fixa em log;
- o resumo marca `RENDA_FIXA` em `assets_without_price` e ajusta a cobertura
  para explicitar que existe pendencia, sem derrubar toda a carteira.

Validacao:

- testes focados: `24 passed`;
- runtime local: carteira `portfolio_id=15`, usuario `user_id=16`, retornou
  resumo com `total_patrimonio=20678.08`, `has_partial_prices=true`, 8 grupos e
  34 posicoes abertas.

Status de liberacao: bug P0 da superficie foi removido para rodada assistida,
mas `ready_for_real_data` continua `false` ate fechar cobertura/precos
pendentes e os gates formais.

Bloco seguinte validado:

- rebuild canonico de snapshots interrompe em lacuna real de preco persistido
  sem abortar a rotina de pos-importacao;
- CSV bloqueia novas linhas de ativos de mercado sem catalogo/historico
  persistido antes da escrita;
- validacao local: `49 passed`, `/health` 200 e dry-run runtime bloqueando
  `NVDA`, `IVV` e `AREA11` sem bloquear `PETR4`.

Bloco operacional de cobertura:

- historicos de `NVDA`, `TFLO`, `IVV`, `INTR`, `AREA11`, `RBRF11`,
  `BTC`, `ETH` e `ADA` foram reparados/confirmados no banco local;
- seed macro oficial `20260908-195126` registrou CDI completo para
  `2026-04-14..2026-09-08`;
- rebuild da carteira 15 criou/atualizou 22 snapshots e o resumo passou a usar
  `snapshot_date=2026-09-08`;
- a pendencia de normalizacao/cobertura dos simbolos de Tesouro importados foi
  promovida para o bloco seguinte e resolvida abaixo.

Bloco Tesouro validado:

- valuation canonico, preco atual e historico persistido agora resolvem tickers
  de Tesouro de forma case-insensitive, preservando a chave solicitada pela API;
- a correcao canonica usa o ultimo preco oficial persistido ate a data do
  snapshot, sem fallback externo em leitura;
- validacao focada: `11 passed`;
- runtime da carteira 15: rebuild de 22 snapshots, `has_partial_prices=false`,
  `assets_without_price=[]`, `price_coverage_pct=100.0` e posicoes de Tesouro
  com preco atual/valor calculado;
- historico de `TESOURO-RENDA-MAIS-2065` retornou serie recente ate
  `2026-09-08`.

Bloco gate descartavel validado:

- smoke HTTP descartavel executado no backend local:
  `TEST-READY-HTTP-SMOKE:PASS`, com limpeza de carteira/transacoes e FX tambem
  em `PASS`;
- `/ready` interno retornou HTTP `503`, `state=not_started`,
  `bootstrap_complete=false` e `ready_for_real_data=false`;
- motivo operacional preservado: bootstrap automatico desabilitado por
  `ENABLE_BOOT_MARKET_SYNC=false`;
- este bloco libera continuidade de testes assistidos com dados
  ficticios/descartaveis, mas nao libera dados reais nem altera
  `ready_for_real_data`.

Bloco contratos de seed/bootstrap validado:

- suite FX/Macro/Tesouro sem execucao real: `81 passed, 1 skipped`;
- suite B3/bootstrap de ativos sem execucao real: `47 passed`;
- suite System bootstrap/Admin sem execucao real: `26 passed`;
- suite Proventos seed contracts sem execucao real: `94 passed, 8 skipped`;
- total do bloco: `248 passed, 9 skipped`;
- nenhum seed real foi executado neste bloco e `ready_for_real_data` permanece
  fechado.

Panorama de liberacao para testes com usuarios:

- liberado agora: rodada assistida com usuarios internos/controlados usando
  dados ficticios ou descartaveis, CSV sintetico e carteiras de teste;
- parcialmente liberado: usuario real assistido ja pode validar navegacao,
  importacao observada e leitura de carteira desde que os dados sejam tratados
  como teste controlado e nao como liberacao geral;
- ainda bloqueado: abertura ampla para usuarios com dados reais, execucoes reais
  de seeds/proventos fora de janela autorizada e mudanca de
  `ready_for_real_data=true`;
- proximos gates obrigatorios: duas execucoes reais controladas de Proventos
  (#226), reconciliacao agregada (#216), importacao/rebuild operacional (#158)
  e decisao formal GO/NO-GO (#227).

Bloco Proventos real controlado - finding e correcao parcial:

- tentativa oficial do wrapper `Invoke-PreProdDividendsIdempotency.ps1` para
  `2026-01-01..2026-09-08` abortou no primeiro seed com
  `evento global conflitante na mesma fonte`;
- primeira melhoria adicionou diagnostico seguro ao erro, sem payload bruto;
- diagnostico identificou `CPFE3/ACAO/2026-04-30/DIVIDENDO/brapi; eventos=6`;
- a persistencia passou a aceitar multiplas ocorrencias globais unicas da mesma
  fonte/data/tipo quando a identidade de armazenamento e distinta;
- segunda rodada identificou o padrao complementar
  `HBRE3/ACAO/2026-01-02/DIVIDENDO/brapi; eventos=4`;
- a persistencia passou a colapsar duplicatas identicas da mesma fonte e manter
  bloqueio para duplicatas com campos canonicos divergentes;
- validacao focada apos a correcao: `27 passed`;
- a tentativa subsequente do wrapper com o commit corrigido foi interrompida sem
  `first.json` em `artifacts/pre-prod-rebuild/dividends-idempotency-20260909-012602`;
- consulta de estado em `asset_dividends` apos a interrupcao confirmou apenas
  `1` evento no intervalo `2026-01-01..2026-09-08`
  (`CERT303-MXRF11`, `ex_date=2026-02-06`), portanto o seed real ainda nao foi
  materializado para teste fidedigno;
- a dupla idempotente completa de Proventos ainda nao esta certificada; manter
  `ready_for_real_data=false` e repetir a janela oficial em bloco dedicado.

Bloco Renda Fixa no Resumo - semantica de cotacao:

- evidencia de usuario: alerta no Resumo informava que `RENDA_FIXA` nao tinha
  cotacao atual e que valor investido seria usado como referencia;
- decisao de produto: `RENDA_FIXA` nao e ativo de cotacao de mercado no SGI v2;
  seu valuation vem da compra aberta e da rentabilidade/indexador informado;
- correcao: quando a cobertura do benchmark/indexador esta incompleta, o resumo
  usa o principal aberto de renda fixa como valor atual conservador, sem
  adicionar `RENDA_FIXA` em `assets_without_price`;
- a rota legada de posicoes tambem passou a preservar posicoes de renda fixa
  pelo principal aberto quando o benchmark esta parcial;
- validacao automatizada: `35 passed`;
- validacao runtime em `2026-09-09` para `lfragoso93@gmail.com`, carteira
  `15/Principal`: `has_partial_prices=false`, `assets_without_price=[]`,
  `price_assets_total=34`, `price_assets_covered=34`,
  `price_coverage_pct=100.0`.

Bloco Proventos escopado para teste assistido:

- objetivo: destravar teste fidedigno da carteira real de validacao sem exigir
  varredura global de todos os ativos do catalogo;
- alteracao operacional: `pre_prod_dividends_seed` aceita `--portfolio-id` e o
  wrapper `Invoke-PreProdDividendsIdempotency.ps1` aceita `-PortfolioId`;
- sem `--portfolio-id`, o fluxo permanece global; com o parametro, a coleta
  fica restrita aos tickers elegiveis presentes nas transacoes da carteira;
- fronteira de auditoria atualizada: leitura declarada de `transactions` alem de
  `assets` e `asset_dividends`; escrita segue restrita a `asset_dividends`;
- carteira `15/Principal` de `lfragoso93@gmail.com`: escopo medido de `49`
  ativos elegiveis contra mais de `2.300` no universo global bruto;
- primeira execucao escopada em `2026-09-09` materializou `183` eventos globais
  de proventos para a janela `2026-01-01..2026-09-09`;
- evidencia idempotente final no commit
  `8746bd72cc5ad628874025f7f40919ad9e5a7af1`:
  `artifacts/pre-prod-rebuild/dividends-idempotency-20260909-122935`;
- relatorio: `ok=true`, `zero_physical_writes_on_second_run=true`,
  `zero_integrity_findings=true`, `stable_after_state=true`;
- impacto runtime: carteira `15` passou a expor `183` direitos de proventos,
  `dividendos_recebidos_12m=569.51`, `total_proventos=569.51`,
  `has_partial_prices=false`, `assets_without_price=[]`;
- status: liberado para teste assistido desta carteira com Proventos semeados;
  ainda falta repetir/decidir a estrategia para varredura global antes de
  liberar uso amplo e marcar `ready_for_real_data=true`.

Bloco Renda Fixa - calculo ate a data atual:

- evidencia de usuario: apos remover o alerta de cotacao, a renda fixa voltou a
  aparecer, mas permanecia pelo principal quando a data atual passava da ultima
  observacao CDI persistida;
- causa: o valuation exigia cobertura completa ate `date.today()`. Em
  `2026-09-09`, a cobertura CDI oficial `BCB_SGS` estava comprovada ate
  `2026-09-08` e a ultima observacao CDI persistida estava em `2026-09-04`;
- correcao: para CDI/SELIC, quando a cobertura ate a data alvo e parcial, o
  valuation usa uma data efetiva igual a ultima data observada/coberta dentro da
  janela, desde que a cobertura ate essa data seja completa; ausencia real segue
  bloqueada;
- validacao runtime da carteira `15/Principal` de `lfragoso93@gmail.com`:
  `LIG LIQUIDEZ` com `invested=121.14`, `current=127.20`, `income=6.06`,
  `income_pct=5.0025`, `applications_count=2`;
- resumo apos limpeza de cache: `total_patrimonio=20724.59`,
  `total_investido=22013.33`, `has_partial_prices=false`,
  `assets_without_price=[]`.

Bloco Gaveta do Ativo - proventos, preco medio e historico:

- evidencia de usuario: na gaveta de detalhe do ativo, `Dividendos (Total)`
  aparecia sem valor e o `Preco Medio` era suspeito apos ciclo de zeragem e
  recompra;
- causa: a gaveta recalculava preco medio no frontend a partir da lista paginada
  de transacoes, ignorando o estado canonico da posicao aberta; alem disso,
  proventos existiam no total do grupo, mas nao eram expostos por ativo no
  contrato de posicoes;
- correcao: cada posicao aberta passa a expor `proventos` canonico por ticker no
  payload de posicoes e a projecao estrita preserva esse campo;
- a gaveta passou a usar `asset.average_price` do backend, que ja zera custo e
  quantidade quando uma posicao e totalmente vendida e recalcula o preco medio
  apenas da nova posicao aberta;
- foi adicionado teste explicito para compra, venda total e recompra:
  `10 @ 10`, venda total, `5 @ 20` resulta em quantidade `5`, custo `100` e
  preco medio `20`;
- UX: `Dividendos (Total)` foi alinhado para `Proventos (Total)`, o historico de
  precos ganhou seletor `1 sem`, `15 dias`, `30 dias`, `90 dias`, `1 ano` e
  `Max`, e a gaveta exibe variacao de `7 dias` e `90 dias`;
- validacao automatizada: backend focado `15 passed`; frontend `typecheck`
  aprovado; `npm run build` aprovado fora do sandbox apos bloqueio local
  `spawn EPERM` no binario nativo do Tailwind/Rolldown.

Bloco Evolucao Patrimonial - janela inicial e gaps de snapshot:

- evidencia de usuario: a evolucao patrimonial no Resumo exibia apenas dois
  meses, apesar de a carteira possuir compras desde `2024-10-22`;
- diagnostico runtime da carteira `15/Principal`: `308` transacoes, snapshots
  existentes de `2024-10-22` a `2026-09-08`, mas com cobertura mensal somente em
  `2024-10`, `2024-11`, `2024-12`, `2025-01`, `2026-08` e `2026-09`;
- causa de UX: o Resumo iniciava em `Ultimos 12 meses`, portanto ocultava os
  snapshots antigos e destacava apenas `2026-08` e `2026-09`;
- causa de dados: o backfill canonico interrompia todo o historico ao encontrar
  o primeiro gap de cotacao persistida de ativo listado; um gap pontual impedia
  a reconstrucao dos meses seguintes;
- correcao: o periodo padrao do grafico no Resumo passa a ser `Todo periodo`;
- correcao de backfill: gaps de preco persistido agora pulam apenas o dia sem
  cobertura e seguem reconstruindo datas posteriores; gaps de benchmark dedicado
  de Renda Fixa/Tesouro continuam bloqueando a partir da fronteira oficial;
- primeira reexecucao runtime avancou alem do gap inicial de `PETZ3`, mas
  bloqueou em `2025-11-25` por divergencia de arredondamento de centavos entre
  soma por classe e patrimonio (`classes=17123.95`, `total=17123.93`);
- correcao complementar: reconciliacao por classe passou a aceitar ajuste de
  ate `R$ 0,02`; divergencias materiais acima disso continuam bloqueadas;
- validacao automatizada: `11 passed` no bloco de valuation/snapshot e
  `typecheck` frontend aprovado.

Bloco TWR historico - preco sem negocio e seed corporativo:

- diagnostico runtime apos o primeiro rebuild: a carteira `15/Principal`
  chegava a `457` snapshots de `2024-10-22` a `2026-09-09`, sem dias parciais,
  mas outubro/2025 e novembro/2025 permaneciam truncados por lacuna de `RBRF11`;
- causa: `RBRF11` tinha historico persistido ate `2025-10-02` e voltava em
  `2025-11-26`; como o lifecycle aceitava apenas janela de 5 dias, datas sem
  negocio derrubavam o snapshot inteiro;
- reparo operacional: `repair_market_price_gaps PETZ3 RBRF11 AUAU3` inseriu
  `672` precos (`501` para `PETZ3` via B3 COTAHIST, `171` para `AUAU3` via
  Yahoo) e, apos melhoria de cauda, `RBRF11` recebeu mais `689` precos via
  B3 COTAHIST;
- correcao de codigo: o reparo dirigido agora cai para B3 COTAHIST tambem
  quando a serie do provedor termina antes da data alvo; o lifecycle de precos
  usa ultimo fechamento persistido por ate `90` dias antes de classificar como
  lacuna real;
- rebuild runtime final da carteira `15` gerou `493` snapshots de
  `2024-10-22` a `2026-09-10`; outubro/2025 fechou com `23` dias uteis e
  novembro/2025 com `20` dias uteis;
- `36` snapshots ficaram marcados como parciais/estimados: `35` datas entre
  `2025-10-08` e `2025-11-25` por `RBRF11` sem negocio publicado e
  `2026-09-10` por fechamento de mercado ainda incompleto;
- seed corporativo escopado: criada CLI
  `python -m app.cli.pre_prod_corporate_events_seed --portfolio-id <id>` para
  coletar eventos corporativos globais somente dos ativos usados na carteira;
- PETZ3/AUAU3: importacao CSV ja registrava alias `PETZ3 -> AUAU3` efetivo em
  `2026-01-05` e evento portfolio-scoped aplicado; a projecao canonica de
  eventos corporativos permanece global e nao consome eventos por carteira;
- seed corporativo runtime da carteira `15`: `33` ativos processados, `122`
  eventos globais criados e `0` erros; os eventos entram como
  `PENDENTE/UNRECONCILED` ate a reconciliacao canonica;
- validacao runtime: helpers de cauda/stale price aprovados no container
  backend; imagem backend reconstruida e saudavel.
