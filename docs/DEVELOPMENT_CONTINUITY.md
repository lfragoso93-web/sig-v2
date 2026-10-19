# Continuidade de desenvolvimento — SGI v2

> Documento de retomada do trabalho. Baseline atualizada em 17/10/2026; ver
> `docs/DEVELOPMENT_BASELINE_2026-10-16.md` para evidências e artefatos.

## Estado atual

- Branch obrigatoria: `stable-15jun`; HEAD no inicio deste bloco `f2e12eec6907ed1cc6880b47090d9b92681b3e56`, igual a `origin/stable-15jun`.
- O working tree ja continha documentacao, calculadora #359 e artefatos `.tmp-candidate-*`; os itens temporarios foram preservados e nao fazem parte desta entrega.
- Ambiente unico de testes assistidos: Compose `sig-v2` pelo Cloudflare Tunnel. Nao usar `sgi-usertest`; DB, Redis, volumes e tunnel devem permanecer.
- UX de Renda Fixa em implementacao: tratamento fiscal derivado do tipo no frontend/API; titulo inclui emissor; carencia oculta/limpa com liquidez diaria; comparador #359 usa a mesma taxonomia.
- Testes focados: frontend 31 aprovados; backend do servico de contratos 20 aprovados; typecheck aprovado.
- Publicacao concluida em `sig-v2`: backend/frontend usam o commit `8391474917684caa4e92f30d8b7c00cdb7ac5a28`; `/health=200`, rota publica e bundle do simulador respondem 200; Alembic `20261017_fixed_income_contracts (head)`. IDs: backend `sha256:35970f9574348e8d7199354694130d9e3a8997de868ae2a2ba711f6515436cfd`, frontend `sha256:93259e4a5649d667385dd21ce359334d94c807ad02557434176ceb3f0e1ae162`.
- `/ready=503` continua fail-closed porque a certificacao persistida nao corresponde a nova identidade. Conforme decisao do usuario, nenhuma certificacao/evento foi promovido e readiness nao bloqueia os testes assistidos. DB, Redis, volumes e Cloudflare Tunnel foram preservados.

## Proximo caminho

1. Atualizar a imagem unica `sig-v2`, preservando servicos de dados e volumes.
2. Registrar digests ativos, health, migration e verificacoes de rota/bundle apos o deploy.
3. Continuar validacao visual desktop/mobile e acessibilidade quando houver sessao de navegador; nao bloquear o desenvolvimento por certificacao de dados reais.

## Mapa de Issues abertas

- Gate financeiro/factual: #149 e #370.
- Segurança, backup e governança: #408, #83 e #293.
- Schema: #272.
- OCI, backlog fora do caminho local: #284.
- Providers/bootstrap: #127, #130 e #253.
- UX e detalhe de ativo: #58, #90, #351 e #353.
- Renda Fixa e ferramentas: #355–#359.
- Metas, Analysis Engine e IA: #246, #360 e #361.
- OAuth: #97.

O inventário de 16/10 encontrou 23 Issues abertas e nenhuma PR aberta. Consulte
`docs/ISSUE_GOVERNANCE.md` para os estados e dependências, e o inventário
GitHub ao vivo antes de encerrar ou reordenar trabalho.

## Contratos que permanecem obrigatórios

- `transactions` é a fonte canônica do lifecycle financeiro; não reconstruir
  ledger paralelo para Tesouro, Renda Fixa ou eventos corporativos.
- Leituras financeiras são DB-first; ausência de preço, FX, evidência de evento
  ou cobertura fica explícita, sem inventar valores ou datas.
- Eventos corporativos conflitantes ou com liquidação não comprovada ficam fora
  da projeção canônica; transações históricas não são mutadas.
- Backups e seeds operacionais precisam ser auditáveis e vinculados ao SHA e
  dataset exatos.
- A promoção #384 é append-only e DB-first. `GO_ASSISTED` não promove dados
  reais; `/ready` fica fechado quando a identidade diverge ou está incompleta.
- Não usar `docker compose down -v`, remoção de volume, prune de volumes,
  `git reset --hard`, `git clean`, rebase de histórico publicado ou force-push.

## Documentação canônica

- `docs/DEVELOPMENT_BASELINE_2026-10-16.md` — fotografia do checkout e runtime.
- `ROADMAP.md` — sequência de desenvolvimento.
- `docs/ISSUE_GOVERNANCE.md` — hierarquia e estados das Issues.
- `docs/architecture.md` e `docs/CORPORATE_ACTIONS.md` — contratos vivos.
- `docs/USER_TEST_READINESS_GATE.md` e `docs/USER_VALIDATION_RUNBOOK.md` —
  testes assistidos.
- `docs/REAL_DATA_CERTIFICATION_RUNBOOK.md` e `docs/CERTIFICATION_PROOF.md` —
  identidade e certificação persistente.
- `docs/operations.md` e `docs/PRE_PROD_REBUILD_RUNBOOK.md` — backup e operação.

Changelogs e documentos em `docs/changelog/` preservam evidência histórica; não
devem ser reescritos como se descrevessem o runtime atual.

## Atualizacao factual — 17/10/2026

O runtime foi consultado no Docker: backend healthy, imagem rotulada com o SHA `5c4ad3906475316294196a826ff140cb3e4bf950`, `ENVIRONMENT=production`, branch `stable-15jun`, dataset `pre-prod-backup.v3:sha256:7d97c52de9ae58ad457f3ffe25055a9963a6a0dea4c9690b8dc72f900fa7133e`, Alembic `20261016_corp_ev_effective_date` e `/ready=200` (`ready_for_real_data=true`, evento 6 persistido). A certificacao vale somente para essa identidade.

O checkout/runtime estao em `5c4ad3906475316294196a826ff140cb3e4bf950`; `origin/stable-15jun` local permanece em `b37661921e3a8455f45c8b676b28955d6ad3d0ea` (tres commits atras). O SHA remoto vivo nao foi confirmado e nenhum push foi feito. Quatro itens `.tmp-candidate-*` preexistentes foram preservados.

Issues #83, #293 e #408 foram consultadas ao vivo e permanecem abertas. A prova recente de #83 cobre backup/restore por funcoes de servico e reconciliacao estrutural em banco descartavel, mas nao autentica/audita/consulta status via API administrativa. #408 aguarda confirmacao CodeQL posterior as correcoes. GOV-07/#293 aguarda correlacao final do inventario integral. Esses status prevalecem sobre fotografias anteriores neste documento; os registros historicos permanecem preservados.

Qualquer novo SHA implantado exige novo backup v3, restore, proof, gates e dry-run vinculados a identidade nova. A promocao anterior certifica apenas `5c4ad390`.
## Revisao do bloqueio de certificacao por SHA — 17/10/2026

A certificacao atual nao bloqueia startup nem `/health`: o Compose considera o backend saudavel por healthcheck separado. `/ready` e a autoridade fail-closed para a capacidade declarada `ready_for_real_data`; seu leitor compara ambiente, branch, SHA completo, dataset, Alembic, gate #227 e PR #362. `GO_ASSISTED` e diagnostico separado. O Compose observado e o ambiente production com o banco atual; nao foi identificada uma stack isolada de testes de usuario nesta verificacao.

Conclusao de arquitetura para o proximo bloco: remover a recertificacao como exigencia de cada iteracao de desenvolvimento pode reduzir a friccao, mas remover ou afrouxar o fail-closed do ambiente que usa o dataset real tambem libera uma identidade de codigo nao avaliada para operacoes financeiras. O caminho seguro a desenhar e separar deploy/teste assistido de ativacao para dados reais, com dataset isolado e controle de acesso para usuarios convidados; a promocao para uso amplo com dados reais continua vinculada a evidencia. Nenhuma regra de runtime foi alterada nesta revisao; a politica ainda precisa ser escolhida antes de mudar o contrato da #384 ou `/ready`.
## Proximo bloco — 17/10/2026

#83 foi fechada no GitHub apos o ensaio HTTP integrado em bancos descartaveis. O procedimento e os limites restantes estao em `docs/ADMIN_BACKUP_RESTORE_REHEARSAL.md`. Proximo bloco unico: confirmar CodeQL pos-correcao (#408). Depois disso, concluir GOV-07/#293 e escolher uma entrega de produto. Os passos anteriores deste documento sao fotografias da retomada de 16/10.

## Resultado da correlacao GOV-07 — 17/10/2026

Inventario GitHub ao vivo encontrou 22 Issues abertas e nenhuma PR aberta. A
correlacao do snapshot local nao encontrou Issue claramente duplicada ou sem
destino. #83 esta fechada; #353 ja possui scroll restoration global e testes
unitarios, restando validacao desktop/mobile. #149, #370, #408 e #272 conservam
residuos factuais/tecnicos distintos; as demais Issues sao backlog de produto,
providers, bootstrap ou OCI conforme `docs/ISSUE_GOVERNANCE.md`.

A ponta remota de `stable-15jun` nao pode ser associada ao checkout local: a
comparacao GitHub informa 7 commits a frente e 0 atras de `main`, mas nao fornece
o SHA da ponta; `git ls-remote` falhou por indisponibilidade de rede. GOV-07 foi
correlacionada para o snapshot disponivel, mas #293 permanece aberta ate a
reconciliacao/publicacao do estado documental. Nenhuma mudanca runtime ou de
certificacao foi feita.

## Revisao da evidencia CodeQL #408 — 17/10/2026

A Issue foi consultada ao vivo: o corpo informa que CodeQL pos-correcao ainda
esta pendente, mas um comentario remoto afirma que o deep scan confirmou CodeQL
e Trivy verdes e que os findings nao aparecem na `stable-15jun`; o mesmo
comentario condiciona o fechamento a propagacao para `main` e confirmacao global.
O workflow configurado e manual/semanal e inclui dois jobs CodeQL e um Trivy da
imagem backend. O conector GitHub disponivel neste ambiente retorna somente
execucoes associadas a PR e nao disponibiliza consulta de runs schedule/manual,
alertas CodeQL ou dispatch. Assim, nao foi possivel reconciliar o resultado nem
confirmar alertas em ambas as branches; #408 segue aberta. Nao foi repetido o
workflow completo e nao houve alteracao de runtime. Retomar quando for possivel
consultar a execucao existente e os alertas para `stable-15jun` e `main`.

## Bloco ambiente de testes isolado — 17/10/2026

Foi criada `docker-compose.usertest.yml` e seu runbook
`docs/USER_TEST_STACK.md`. A stack `sgi-usertest` separa banco/artefatos e
identidade do runtime `sig-v2`, nao carrega `.env`, nao expoe backend/DB/Redis
ao host e publica frontend apenas em loopback. Ela remove a certificacao de
dados reais do ciclo cotidiano de desenvolvimento; `/ready` e promocao real
continuam preservados para a stack que opera dados reais.

O container `sig-v2` inspecionado antes da alteracao estava saudavel e
pertence ao projeto existente. A stack `sgi-usertest` subiu com backend,
PostgreSQL e Redis saudaveis; Alembic em `20261016_corp_ev_effective_date`,
`/health=200`, frontend loopback `127.0.0.1:18080=200` e identidade de teste
com SHA igual ao checkout. `/ready=503` por `runtime_identity_error` e esperado
nesse ambiente sem dataset real/certificacao. A imagem principal e seu
banco/volume nao foram alterados. Detalhes e digests em `docs/USER_TEST_STACK.md`.

Atualizacao da calculadora #359 — 17/10/2026: a stack `sgi-usertest` foi
reconstruida apos a implementacao local. Typecheck, build de producao e quatro
testes deterministas passaram; `/health`, rota SPA e asset JS responderam 200.
A imagem referencia `5c4ad3906475316294196a826ff140cb3e4bf950` como SHA base,
mas incorpora arquivos locais nao commitados; nao representa SHA reproduzivel
nem certificacao real. `/ready=503` continua esperado para identidade sintetica.
Validacao visual desktop/mobile permanece pendente porque o navegador integrado
nao estava disponivel. A stack principal `sig-v2` permaneceu parada e intocada.
Digests e verificacoes operacionais estao em `docs/USER_TEST_STACK.md`.

## Entrega parcial da #359 — 17/10/2026

Foi adicionada a frente A (calculadora de rendimentos) em
`/carteira/ferramentas/rendimentos`, com projeção de taxa efetiva anual e aporte
mensal no fim de cada período. O fluxo é frontend-only e não lê nem grava dados
de carteira. Fórmula, premissas e limites estão em `docs/TOOLS_CALCULATORS.md`.
Testes deterministas, typecheck e build passaram na atualizacao descrita acima;
a revisao visual desktop/mobile permanece pendente por indisponibilidade do
navegador integrado. A calculadora de Renda Fixa continua fora deste bloco.

## Inventario estatico de Renda Fixa #355 - 17/10/2026

O inventario de schema, API, formulario, CSV, valuation, snapshots e TWR foi
registrado em `docs/FIXED_INCOME_TAXONOMY_INVENTORY.md`. Confirmou dados de
contrato serializados em `transactions.notes`, writer canonico compartilhado e
remocao irreversivel da antiga tabela de projecao. A auditoria DB-only da stack
de testes validou a identidade sintetica e encontrou zero transacoes. A
auditoria remota de setembro segue historica.

## Implementacao inicial de contratos de Renda Fixa #355 - 17/10/2026

Foi preparada implementacao local aditiva de `fixed_income_contracts` e da
ligacao nullable em `transactions`, com API portfolio-scoped, validacao no
writer canonico e limpeza da ligacao ao editar a classe para fora de Renda
Fixa. Foram incluidos cenarios unitarios e a migration
`20261017_fixed_income_contracts`. A validacao permanece incompleta: pytest
local nao iniciou por ausencia de `pydantic`; o rebuild de `sgi-usertest` falhou
com BuildKit `error reading from server: EOF`, e as consultas subsequentes ao
daemon Docker ficaram sem resposta. Portanto, a migration nao foi aplicada, a
imagem nao foi atualizada e nenhum teste de runtime/PostgreSQL foi confirmado.
Nenhum dado existente foi associado ou alterado. Retomar verificando/restaurando
o daemon e executar testes focados e migration em banco descartavel antes de
considerar este bloco validado. A stack principal `sig-v2` nao foi alvo de
comandos de alteracao.


### Retomada operacional e validacao #355 - 17/10/2026

O Docker voltou a responder. Rebuild isolado concluido; o alvo de migration agora
e configuravel por ambiente, mantendo o pin `20261016_corp_ev_effective_date`
como default e escolhendo `head` somente em `sgi-usertest`. A imagem de backend e
a de frontend foram atualizadas e seus digests estao em
`docs/USER_TEST_STACK.md`. Migration em head, 18 testes passaram sem avisos ORM,
API consta na OpenAPI, `/health=200` e frontend local=200. `/ready=503` e esperado
para a identidade de testes sem dados reais. Exercicio PostgreSQL em transacao
com rollback rejeitou ligacao cross-portfolio e deixou zero carteiras, transacoes
e contratos. Nenhuma operacao foi feita na stack principal.


### Integracao do formulario de Renda Fixa #355 — 17/10/2026

O formulario de transacoes passou a consumir a API de contratos: cria o contrato no mesmo unit of work do lancamento, permite selecionar contrato existente, mantem associacao durante edicao e conserva quantidade/preco originais. Linhas legadas sem contrato continuam editaveis; o CSV legado segue sem campos novos e nao recebe associacao automatica. Validacao: 16 testes de frontend focados, `npm run typecheck` e quatro testes backend focados passaram.

BuildKit encerrou a primeira exportacao com `error reading from server: EOF`; o Docker Desktop foi reiniciado e o rebuild isolado concluido. Backend e frontend em execucao correspondem as novas imagens; migration `20261017_fixed_income_contracts` esta em head. `/health=200`, frontend `127.0.0.1:18080=200`, `/ready=503` esperado para identidade sintetica. PostgreSQL confirmou zero transacoes e zero contratos. Nenhum dado financeiro foi criado, nenhum backfill foi feito e a stack principal permaneceu fora da operacao. Esta atualizacao substitui as notas anteriores que diziam que a integracao de formulario nao existia.

O proximo bloco e suportar metadados de contrato por colunas explicitas no CSV de importacao/exportacao, sem inferencia para arquivos antigos.


### CSV de contratos de Renda Fixa #355 - 18/10/2026

O modelo CSV foi estendido com campos opcionais `fixed_income_*` e `fixed_income_contract_key`. A chave agrupa aplicacoes do mesmo contrato dentro daquele arquivo; termos inconsistentes para a mesma chave falham no dry-run. A importacao usa o writer canonico, cria no maximo um contrato por chave e preserva commit/rollback do lote. Metadados em outras classes sao rejeitados. CSV legado de nove colunas continua sem inferencia nem link automatico. A exportacao `GET /api/v1/portfolios/{portfolio_id}/export-csv` verifica ownership, devolve o ledger e os termos de contrato, e produz chaves locais ao arquivo em vez de IDs internos. O modal oferece o download autenticado por blob.

Validacao: 82 testes backend CSV/fixture sintetico passaram na imagem atualizada; 7 testes frontend, `npm run typecheck`, `npm run build` Docker e Flake8 com E501/W293 ignorados passaram. A execucao Flake8 sem ignores mostrou apenas avisos legados de comprimento de linha/espacos em branco, mais os imports de reexportacao corrigidos nesta etapa.

### Hierarquia e metadados fiscais no formulario de Renda Fixa #355 - 18/10/2026

Feedback da revisao visual: tipo de produto deve ser a primeira escolha dos
dados do contrato, antes do indexador, pois a classificacao orienta as demais
condicoes. O modal foi reorganizado nessa ordem. Produtos com tratamento
usualmente isento (LCI, LCA, LIG, CRI, CRA e debenture incentivada) passam a
sugerir `tax_exempt=true`; para os demais, a UI deixa nao informado. A sugestao
e editavel e orienta confirmar emissao/titular/documentos. Nao altera o motor de
IRPF e nao deve ser interpretada como calculo ou aconselhamento fiscal.
Acrescentada regressao de ordem, sugestao e preservacao de escolha manual.
Validacao: 14 testes do modal, typecheck e build Docker passaram. Imagem
frontend aplicada a `sgi-usertest`; frontend 200 em `127.0.0.1:18080`, backend
`/health=200`, `/ready=503` esperado para identidade sintetica. Alembic segue
`20261017_fixed_income_contracts (head)`; banco e volumes preservados; stack
principal nao tocada.

O container backend manteve a imagem existente
`sha256:1495e3127f0b938d7b6ac3a2152eb3bb5ed01c94311a371b6cbcb020cb98f776`.
A nova imagem frontend em execucao e
`sha256:9cedcea08da45ee3d07055fd98bc45e9d5c5e586d681f44b4bccff1f7c368b8d`.
Como o working tree permanece com alteracoes locais, `APP_COMMIT_SHA` e apenas
o SHA base e esta imagem nao e release reproduzivel nem certificacao de dados
reais.


### Associacao automatica e prefill por instrumento #355 - 18/10/2026

O seletor explicito de contrato foi removido do fluxo normal. Ao gravar novos
termos, o service agora reutiliza um contrato da mesma carteira somente quando
todos os termos tipados e o nome (case-insensitive) coincidem; ticker sozinho
nao funde produtos diferentes. O atalho do resumo carrega dados de contrato
quando o nome/codigo da posicao aponta para uma unica correspondencia; vinculos
existentes tambem hidratam os campos do modal. O atalho Tesouro da pagina agora
passa vencimento conhecido e preserva a consulta do catalogo para indexador,
taxa e PU. Nao houve alteracao do ledger ou migracao.

Validacao local: typecheck passou e o build Docker do frontend compilou. O
build combinado perdeu o BuildKit durante a exportacao/unpack da imagem
backend (`error reading from server: EOF`); em seguida o Docker Desktop
reportou falha ao iniciar a engine WSL (`0xc00000fd`). Portanto, nao foi
possivel confirmar o estado dos containers nem aplicar as imagens. Nenhum
teste foi adicionado/executado nesta alteracao. A retomada deve primeiro
recuperar o Docker, inspecionar `sgi-usertest` e entao rebuild/recriar e checar
`/health`, `/ready`, frontend e imagem efetivamente ativa.

#### Recuperacao e implantacao - 18/10/2026

O Docker voltou a responder sem reiniciar o engine. O rebuild foi concluido e
somente backend/frontend de `sgi-usertest` foram recriados; PostgreSQL, Redis e
volumes permaneceram ativos. As imagens efetivamente em execucao sao backend
`sha256:598f73a8fc949493e25a919b4449992b6e40f5449b1bbd9ba6ba11ec710b929d` e
frontend `sha256:7224856e167182dab7db87f49c69a92a2ba88bb1d4d445b5eace5666d8b57169`.
Typecheck passou; Alembic `20261017_fixed_income_contracts (head)`,
`/health=200`, `/ready=503` esperado, endpoint de contratos na OpenAPI e
frontend `127.0.0.1:18080=200`. Nenhum teste foi adicionado ou executado. A
validacao visual/funcional de agrupamento continua sendo o proximo bloco.

O primeiro build combinado encerrou com `error reading from server: EOF` apos exportar e registrar as imagens. Apos reiniciar o Docker Desktop, o daemon voltou a responder; o backend foi reconstruido em comando isolado e os containers backend/frontend de `sgi-usertest` foram recriados. Backend healthy, PostgreSQL/Redis healthy, frontend `127.0.0.1:18080=200`; `/health=200`; rota no OpenAPI; exportacao sem autenticacao retorna 401. `/ready=503` e esperado para identidade sintetica. Alembic `20261017_fixed_income_contracts (head)`; PostgreSQL confirma zero transacoes e zero contratos.

Identidade de origem: checkout `stable-15jun` em `5c4ad3906475316294196a826ff140cb3e4bf950`, tres commits a frente de `origin/stable-15jun` (`b37661921e3a8455f45c8b676b28955d6ad3d0ea`), confirmado tambem pela API GitHub em 18/10. Nao ha PR aberta. A arvore tem varias alteracoes locais preexistentes e as imagens incluem o estado de trabalho nao commitado; `APP_COMMIT_SHA` aponta apenas para o HEAD base. A stack principal nao foi rebuildada, migrada ou certificada.

### Agrupamento RF - alinhamento documental e normalizacao - 18/10/2026

A Issue #355 foi consultada: seus criterios ainda pedem seletor explicito,
enquanto o fluxo atual e transparente e agrupa por equivalencia de termos na
carteira. A divergencia esta documentada em `ROADMAP.md`; o tracker remoto nao
foi alterado. Revisao do service encontrou que caixa do emissor e espacos
repetidos em nome/emissor podiam impedir reuso. O schema agora colapsa espacos
consecutivos e a equivalencia compara caixa de display_name e issuer sem
sensibilidade a caixa; taxa, unidade, produto, datas, liquidez, tributacao e
moeda continuam exatos. Treze testes focados passaram em SQLite em memoria,
incluindo reuso, termos divergentes e isolamento entre carteiras. A validacao
visual e o teste Vitest permanecem pendentes. Nenhuma escrita persistente foi
realizada; volumes, DB principal e ledger foram preservados.

### Imagem completa para testes assistidos - 18/10/2026

A stack `sgi-usertest` recebeu ambas as imagens atuais: backend
`sha256:93053a6fb003b46b84beaea359235033deb051f4cde3654904e436aaef1cba58` e
frontend `sha256:86b034acfd1ae248af234f6dd97c926c9f74f57ecb8fed5e40d87a9d3a74e3ea`.
O backend, DB e Redis estao saudaveis, Alembic em head, frontend e bundle 200,
e OpenAPI contem contratos RF e exportacao CSV. A base segue sem transacoes,
contratos ou eventos de certificacao. `/ready=503` permanece esperado em
`ENVIRONMENT=testing` sem dataset real. Stack pronta para teste assistido; isso
nao certifica dados reais. A stack principal nao foi atualizada, nenhum volume
foi removido e nao houve publicacao em registry. A validacao visual pelo agente
e o teste Vitest de prefill continuam sem conclusao.

### Correção do destino de testes e publicação da imagem — 18/10/2026

O runtime de validação com usuários é exclusivamente `sig-v2` via Cloudflare
Tunnel (`https://sgi.lfconsultoria.dpdns.org`). O procedimento isolado
`sgi-usertest` fica arquivado e não deve ser iniciado nem atualizado; seus
containers foram parados sem remover volumes. A imagem do backend/frontend da
stack `sig-v2` é o artefato que deve receber cada atualização.

Inventário local: 34 arquivos modificados e 15 novos de produto, agrupados em
importação/exportação CSV e metadados de renda fixa, vínculo de contratos ao
ledger canônico, modal e associação automática, calculadora de rendimentos,
migração Alembic, testes e documentação/governança. Os pacotes `.tmp-candidate-*`
são artefatos locais e não entram no Git nem na imagem.

Validação antes de publicação: backend focado 89/89; frontend Vitest 23/23;
typecheck e build de produção aprovados. O Vitest detectou inicialmente falta
de nome acessível no controle de vencimento; `aria-label="Vencimento"` foi
adicionado e a suíte passou na repetição.

O `.env` de execução já possui os tokens de provedores e do Tunnel; os valores
não foram exibidos. `VITE_API_URL` permanece vazio para usar o proxy Nginx.
Backup consistente pré-migration gerado como `pre-prod-backup.v3`, run
`20261018-183455`, SHA-256 `476cedea77044ccf63198f39d540412538dcc0808deaf57053966fb34978548f`;
nenhuma escrita no banco ocorreu no backup.

Pendente ao registrar esta nota: publicar os commits locais em `stable-15jun`,
definir o alvo runtime para `20261017_fixed_income_contracts`, atualizar apenas
backend/frontend da stack `sig-v2` preservando banco/volumes e validar imagem,
migration, API, `/health`, `/ready` e URL pública. A certificação atual pertence
ao SHA/dataset/revision anteriores; não deve ser atribuída automaticamente à
imagem nova.

#### Resultado da primeira publicação e correção do inventário — 18/10/2026

O commit `1d245ff76ecc4fcf164073c8a731809cb93d2dc9` e os três commits locais
anteriores foram publicados em `origin/stable-15jun` por fast-forward. As imagens
backend `sha256:8e0a516f5376ee6314db01ba72e95eceffb8c8ea5682b517b8ca406764652a53`
e frontend `sha256:8acaec4d92bc6e4588c73b2e129efcdc131bfc24a565aa2cca70609b3d45b4fb`
foram aplicadas ao projeto existente `sig-v2`; Cloudflare Tunnel permaneceu
conectado, banco/Redis e volumes não foram recriados. `/health=200`, API contém
rota de contratos e exportação CSV, URL pública `200`; Alembic chegou a
`20261017_fixed_income_contracts`. `/ready=503` por divergência de SHA e
revision com o evento antigo, sem reaproveitar certificação.

O primeiro backup pós-migration foi bloqueado corretamente pelo inventário, que
marcou `fixed_income_contracts` como tabela desconhecida (vazia, 0 linhas). A
tabela é metadado de contrato informado pelo usuário, ligado ao ledger, e foi
classificada como `preserved`; o teste da política passou (19/19). Nenhuma
escrita financeira ocorreu nessa auditoria.

#### Publicação concluída e validação do Tunnel — 18/10/2026

A correção de inventário foi publicada no commit `82e896e146152f85dcd31610f169e3483545e2af`.
A imagem backend foi reconstruída e aplicada à stack `sig-v2`; digest efetivo
`sha256:4a69a849f2e66ede2934970ef45ec46bd303bfa0eb34ec3049c8184f258bb2d0`. O
frontend permanece no digest `sha256:8acaec4d92bc6e4588c73b2e129efcdc131bfc24a565aa2cca70609b3d45b4fb` e serve o bundle
`/assets/index-CIYn_A9s.js`. A imagem exibe SHA completo
`82e896e146152f85dcd31610f169e3483545e2af`.

O inventário final read-only retornou 26 tabelas, 4.440.517 linhas,
`unclassified_tables=0`, `blocking_findings=0` e zero escritas. O backup
consistente pós-migration `20261018-184424` foi validado; SHA-256
`24349a92bdbc024a633e5a6a662dbf63d19f52780e626fc4da928206f5d33ade`. A CLI
derivou `REAL_DATASET_REFERENCE=pre-prod-backup.v3:sha256:24349a92bdbc024a633e5a6a662dbf63d19f52780e626fc4da928206f5d33ade`; o `.env` local
está alinhado com esse valor, `APP_COMMIT_SHA=82e896e146152f85dcd31610f169e3483545e2af` e
`RUNTIME_MIGRATION_TARGET=20261017_fixed_income_contracts`. Os tokens de
providers e Tunnel continuam configurados e não foram exibidos.

Validação final: DB, Redis e backend healthy; `/health=200`; Alembic
`20261017_fixed_income_contracts`; OpenAPI inclui contrato de renda fixa e
exportação CSV; URL pública e bundle JS retornam 200; sem erros DNS recentes no
Tunnel. `sgi-usertest` está parado, sem containers ativos; volumes foram
preservados e seu compose dedicado foi removido do checkout.

`/ready=503` com `identity_mismatch` nos campos `commit_sha`,
`dataset_reference` e `alembic_revision`, pois o evento de certificação existente
pertence à identidade anterior. Nenhum novo evento foi promovido; readiness
permanece fail-closed e a imagem pode ser validada pelos usuários pelo Tunnel.

### Próximo bloco: validação do fluxo transparente de Renda Fixa — 18/10/2026

O teste focado de `AddTransactionModal` foi retomado e passou: 15 testes,
incluindo produto antes de indexador, sugestões fiscais editáveis, preservação
de lançamentos legados, prefill automático quando há um único contrato e
preservação do vínculo ao editar. A primeira tentativa local do Vitest foi
bloqueada pelo Windows (`spawn EPERM`) antes de iniciar; a repetição com a
permissão de execução necessária concluiu com sucesso.

A validação visual desktop/mobile continua pendente. O runtime do navegador foi
inicializado, mas nenhum navegador conectado foi disponibilizado nesta sessão.
Não foi feita interação nem escrita na aplicação por navegador.

A consulta remota à Issue #355 confirmou que seus critérios ainda pediam um
seletor explícito de contrato, enquanto o produto atual associa automaticamente
por equivalência e pré-carrega os termos pelo Resumo. Os critérios foram
atualizados no GitHub para refletir esse fluxo; a Issue permanece aberta somente
para validação visual e acessível. Também foi confirmado que #359 contém uma
segunda frente de comparação de Renda Fixa, ainda sem premissas tributárias
detalhadas. Não avançar para cálculo de IR sem essas regras. O roadmap aponta a
validação visual como fechamento de #355 e mantém a frente B de #359
condicionada a essas premissas.

Nenhum dado do ledger foi escrito. A imagem existente de `sig-v2` permanece a
publicada; esta rodada alterou apenas documentação local e executou testes
focados. A próxima mudança de produto deve atualizar backend/frontend dessa
mesma stack, preservando DB, Redis, volumes e Tunnel.


## Registro corrente - UX tributaria de Renda Fixa - 18/10/2026

A classificacao fiscal deixou de ser editavel: o tipo canonico de produto alimenta `tax_exempt` no schema e formulario. O comparador #359 usa o mesmo mapeamento. O campo separado de emissor foi removido; o nome do titulo identifica o emissor, preservando dados antigos. Liquidez diaria oculta e limpa vencimento/carencia. Testes focados: frontend 31/31, backend de contratos 20/20, typecheck aprovado. Publicacao concluida: commit `8391474917684caa4e92f30d8b7c00cdb7ac5a28`, backend `sha256:35970f9574348e8d7199354694130d9e3a8997de868ae2a2ba711f6515436cfd`, frontend `sha256:93259e4a5649d667385dd21ce359334d94c807ad02557434176ceb3f0e1ae162`. `/health=200`, rota e bundle publicos 200, Alembic head e DB/Redis saudaveis. `/ready=503` por identidade de certificacao anterior; nao foi promovido evento novo. Validacao visual permanece pendente.

## Navegacao de ferramentas - 18/10/2026

Calculadora de rendimentos e Simulador RF estao agrupados sob **Ferramentas**
na barra lateral. As duas rotas existentes foram mantidas, o grupo expande ao
entrar em uma rota filha e tambem funciona com o menu recolhido. Teste focado
da hierarquia: 3/3; typecheck e build de producao aprovados. Nenhuma alteracao
de backend, banco, Redis, volumes ou Tunnel foi necessaria. A imagem sera
atualizada no servico frontend da stack existente `sig-v2`.

## Acessibilidade automatizada das ferramentas - 18/10/2026

Na Calculadora e no Simulador RF, as dicas foram associadas aos campos,
resumos dos resultados agora usam live region para leitores de tela e tabelas
com rolagem horizontal podem receber foco e anunciam sua finalidade. Testes
focados das duas páginas: 6/6; typecheck aprovado. O navegador integrado não
estava disponível nesta sessão (`agent.browsers.list()` vazio); portanto a
validação visual desktop/mobile ainda não foi feita e as Issues #355/#359
continuam sem fechamento dessa etapa. A imagem frontend da stack `sig-v2` será
atualizada, sem mudanças em backend ou serviços de dados.

## Publicacao do bloco de acessibilidade - 18/10/2026

O frontend do commit `5352ddea1c8e2f0a57ac25fd0f8cd3ef21354f85` foi publicado
na stack existente `sig-v2`. Imagem `sig-v2-frontend:latest`:
`sha256:e82229851445c188c899e5cebe31cc9ad6f1c2f8ef1753197bcb4236e6f0016f`.
As rotas de Calculadora e Simulador RF responderam HTTP 200 e o bundle
`/assets/index-Dm3xHvfF.js` respondeu 200 com `aria-live`, `aria-atomic`,
`aria-describedby` e regioes de tabela presentes. Frontend, backend, DB, Redis e
Cloudflare Tunnel estao ativos; backend, DB e Redis permanecem healthy. Apenas
o container frontend foi recriado. Validacao visual desktop/mobile permanece
pendente por indisponibilidade do navegador integrado.

## Verificacao funcional de Proventos, IRPF e precos - 18/10/2026

Leitura dos logs recentes do backend, sem escrita de dados:

- IRPF: os endpoints canonicos para os anos 2025 e 2026 responderam HTTP 200. O modulo cobre classes suportadas; nao gera nem transmite a declaracao completa e algumas classes ficam fora do calculo.
- Proventos: a pagina principal usa `/portfolios/{id}/proventos`; o painel de detalhe de ativo ainda chamava `/api/v1/dividends?portfolio_id=...` e recebia 404. O hook foi corrigido para a rota por carteira existente e o formato de resposta foi mapeado para o painel. Datas civis usam `formatReferenceDate` para evitar deslocamento de um dia por fuso.
- Precos: a leitura financeira e DB-first, sem cotacao ao vivo na abertura das paginas. Logs registraram preco ausente na data `2026-10-17` para ADA, ALOS3, AREA11, BTC, DIVD11, E1CO34, ETH, NIKE34, NVDC34 e POMO4. Isso nao prova que os demais ativos estejam todos atualizados; a cobertura e o ultimo sync precisam de auditoria dedicada.

Testes focados do hook/painel: 5/5; typecheck e build de producao aprovados. Publicar o frontend corrigido em `sig-v2` depois do commit. Nenhuma alteracao de backend ou escrita em dados financeiros.

Confirmacao apos publicacao do bloco de Proventos (18/10/2026): commit
`4509d3e480df07836af8064dbb6fb7029ce9ca05` enviado a `stable-15jun` e aplicado
na imagem `sig-v2-frontend:latest`, ID
`sha256:f9f2b1f24ef85654f67e68f5fc5abc7f4bfacf36b104ef1cbd6539dae9a6a9d9`.
A URL antiga `/api/v1/dividends?portfolio_id=15` respondeu 404; a rota
`/api/v1/portfolios/15/dividends` respondeu 401 sem autenticacao, confirmando
que o backend reconhece o caminho e exige sessao. As paginas Proventos, IRPF e
Simulador RF responderam HTTP 200, assim como o bundle `index-Co5T9z9c.js`.
Backend, DB e Redis permanecem healthy; Tunnel ativo; so o frontend foi
recriado. A chamada autenticada pelo fluxo real nao foi exercitada nesta
verificacao.

## Auditoria read-only de cobertura de precos - 18/10/2026

A rotina `summarize_asset_price_coverage` foi executada no backend em transacao
PostgreSQL `READ ONLY`; nenhuma sincronizacao, chamada a provider ou escrita foi
feita. No catalogo global (nao equivalente a ativos mantidos por usuarios),
3.677 ativos foram classificados: 2.810 `STALE`, 71 `MISSING`, 6
`PARTIAL_BOTH`, 632 aliases canonicos, 152 com provedor dedicado e 6 sem
cotacao de mercado. 2.338 itens sinalizam intervalos para sincronizacao; parte
das lacunas permanece indisponivel segundo o estado do provider e nao deve ser
fabricada.

Na carteira 15 consultada nos logs recentes, 15 de 15 posicoes de ativos com
cotacao tinham preco persistido e nenhuma estava sem preco. Os timestamps
`last_price_updated_at` variaram de `2026-10-16 21:02:55 UTC` a
`2026-10-16 21:03:03 UTC` (sexta-feira, perto do fechamento em Sao Paulo).
Isso cobre a ultima sessao de bolsa ate 18/10, domingo; nao e cotacao em tempo
real, e nao prova frescor diario de cripto durante o fim de semana. O proximo
bloco deve reconciliar somente posicoes atuais com a cobertura global e montar
um plano de sincronizacao por escopo, sem executar escrita nesta auditoria.

## Validacao de eventos corporativos e estado operacional - 18/10/2026

Checkout stable-15jun em 23c0df2de342868ce989c45993fbd1e75bf39eb4, igual a origin/stable-15jun; runtime de produto segue no commit 8391474917684caa4e92f30d8b7c00cdb7ac5a28, com imagem backend sha256:35970f9574348e8d7199354694130d9e3a8997de868ae2a2ba711f6515436cfd e frontend sha256:f9f2b1f24ef85654f67e68f5fc5abc7f4bfacf36b104ef1cbd6539dae9a6a9d9. Somente documentacao mudou neste bloco; nao houve rebuild nem alteracao do runtime.

Backend, PostgreSQL e Redis healthy; Tunnel e frontend em execucao; /health=200 e Alembic 20261017_fixed_income_contracts (head). /ready=503 segue identity_mismatch para commit, dataset e revisao; nenhuma promocao ou escrita de certificacao foi feita. O endpoint de readiness nao foi usado como criterio de saude da interface para testes assistidos.

Eventos corporativos: 125 registros persistidos, 121 UNRECONCILED, 3 CONFLICT, 1 MATCHED canonico e sem revisao. Tres conflitos ocorrem em datas em que havia operacao/posicao na carteira: AMOB3 e KLBN11; permanecem fora da projecao por desenho fail-closed. Dois eventos B3 de NIKE34 nao tem data efetiva. Nao ha job recorrente de coleta de eventos; a coleta e um estagio de bootstrap opt-in. A Issue #370 permanece aberta pela evidencia externa de KLBN11.

Validacao: 80 testes backend e 6 testes frontend focados em projecao, reconciliacao, lifecycle e fracoes passaram. As rotas aparecem na OpenAPI; GETs sem sessao responderam 401, entao a chamada autenticada via jornada de usuario permanece pendente. Auditoria PostgreSQL em transacao READ ONLY; nenhum dado financeiro foi escrito e nenhum provider foi chamado.

Proximo bloco: auditoria escopada das posicoes atuais versus cobertura de precos, plano de sincronizacao sem execucao implicita, e smoke autenticado das rotas de Proventos, IRPF e eventos. Para fechar eventos, obter evidencia de custodiante antes de qualquer reconciliacao e registrar a data efetiva oficial de NIKE34.
## Classificacao de UNRECONCILED - 18/10/2026

Auditoria read-only do catalogo:
- 121 linhas UNRECONCILED: B3 2 (NIKE34), BRAPI 46 (17 tickers; 28 bonificacoes, 10 splits, 8 grupamentos), Yahoo 72 (17 tickers; 67 splits, 5 grupamentos) e ticker_resolution 1 (PETZ3 para AUAU3).
- 120 sao eventos de provedor globais (portfolio_id nulo); todos os 121 tem asset_id. A excecao e ticker_resolution, uma troca por carteira em 05/01/2026, nao uma acao global de quantidade.
- Os dois eventos B3 aguardam effective_date. Os 118 eventos BRAPI/Yahoo nao tem review_reason persistido; UNRECONCILED/requires_review e estado default da ingestao, nao prova de erro do fato.
- Candidatos exatos cross-provider: zero. Existem 10 pares BRAPI/Yahoo com mesmo tipo/fator e datas a 1-3 dias de distancia. Nenhum dos 118 eventos BRAPI/Yahoo com data efetiva coincidiu com quantidade positiva no ledger existente na data; os dois B3 sem data nao podem ser avaliados assim.
- O reader atual exclui toda linha nova sem MATCHED, embora seja global. A arquitetura precisa selecionar um fato canonico conforme autoridade/fallback do provedor e projetar esse evento globalmente, preservando origem e sem aplicar duplicatas. Nenhuma linha foi promovida ou escrita.

O evento 3 de PETZ3 e uma troca especifica da carteira para AUAU3, marcada APLICADO, mas nao e um dos eventos de split/bonificacao. O subsistema nao encontrou transacoes com o marcador de ledger desse evento. As tres linhas CONFLICT AMOB3/KLBN11 continuam a pendencia material separada da Issue #370.

Proximo bloco atualizado: desenhar e testar a elegibilidade canonica por autoridade de fonte e reconciliar os 10 pares de datas divergentes com a regra oficial de data efetiva. Preservar os conflitos sem evidencia; nao fazer MATCHED em lote.

### Auditoria B3 do catálogo global - 18/10/2026

A consulta read-only do `B3ListedCompaniesClient` cobriu 21 tickers de eventos globais. A auditoria identificou mistura de ISINs, conversao incorreta de percentuais e labels/tipos sem suporte. O normalizador local foi corrigido para filtrar pelo ISIN esperado, converter percentuais de bonificacao/desdobramento e rejeitar tipos desconhecidos. Repetido o dry-run: 17/21 passaram; BBDC3/RANI3 continuam com fator invalido e PETZ3/SANB11 tem tipo nao suportado. Os testes focados terminaram em 22/22 na copia isolada. Nenhuma escrita foi feita e a imagem ativa ainda nao inclui o patch.

Bloqueio antes de seed: tratar os quatro payloads fora do contrato, corrigir por plano auditavel o fator 900 persistido no evento B3 164 de NIKE34 (B3 confirma fator de quantidade 10), obter calendario para resolver a data efetiva e preflight de ledger/fracoes. Gerar backup consistente antes de gravar. A evidencia B3 de AMOB3 confirma grupamento 0,02 em 28/05/2025; para KLBN11 confirma bonificacao de 1% em 17/12/2025. A liquidacao de fracoes continua sem conclusao automatica.

Aplicacao direta autorizada: evento B3 165 de NIKE34 passou para `MATCHED`, com data efetiva 13/10/2026 e `PENDING_SETTLEMENT`. Preflight global: 1 carteira com 6 unidades, projetadas como 1 unidade + fracao pendente 0,2; sem preco/caixa inferidos. Snapshot maintenance: 4 invalidados, 520 reconstruidos, 1 cache de rentabilidade invalidado. Backup v3 consistente anterior a escrita: `20261018-nike34-event165-pre`, SHA-256 `32ea9db5f816beeab5c83386277dfe7493f4c19d26aa5cd61066078354b92711`. O evento 164 e as demais reconciliacoes continuam pendentes.

Publicacao do normalizador B3 no commit `f5cae2ddd21f684b7a1b772ae3e273182497e575`, imagem backend `sha256:26d2c42f35d6ede6bc842cbbadc6c73811cf1347df8211583bacd2d5e976ce6b`. A stack `sig-v2` foi atualizada somente no backend; `/health` OK, Alembic `20261017_fixed_income_contracts (head)`, banco/Redis/frontend/cloudflared ativos. A coleta B3 cobriu 21 tickers: 17 normalizaveis; BBDC3/RANI3 com fator invalido e PETZ3/SANB11 com tipo nao suportado permanecem fora de qualquer escrita. Estado atual: 2 `MATCHED`, 3 `CONFLICT`, 120 `UNRECONCILED`. Proximo: adicionar reparo semantico B3 para o evento 164 NIKE34 (fator 900 para fator oficial 10, identidade e hash de origem), com dry-run e backup antes de qualquer escrita; investigar os quatro payloads bloqueados.

Revisao integral read-only de UNRECONCILED: 120 linhas (119 globais: 1 B3, 46 BRAPI, 72 Yahoo; uma troca ticker-resolution portfolio-scoped). A coleta B3 atual normalizou para 16 tickers, falhando fechado em BBDC3/RANI3 (fator) e PETZ3/SANB11 (tipo). Encontrou 19 correspondencias exatas de tipo/record date/fator, divergencias e 16 acoes sem linha correspondente entre as UNRECONCILED, incluindo 9 direitos de subscricao sem quantidade automatica. Cinco eventos BRAPI carregam labels `INCORPORACAO`, `CIS RED CAP` ou `RESG TOTAL RV` embora o tipo persistido seja `BONIFICACAO`; seis BRAPI, um Yahoo e o B3 164 tem fatores extremos. Dez pares BRAPI/Yahoo permanecem separados por datas a 1-3 dias. Nenhuma posicao positiva foi encontrada nas datas atualmente persistidas para os eventos BRAPI/Yahoo, mas as datas de record date nao estao comprovadas como sessoes efetivas. Nenhuma escrita foi feita.

O utilitario semantico agora aceita B3 somente com consistencia de ISIN, record date, label e fator bruto; corrige fator/ratio e identidade/hash, sem reconciliar nem definir data efetiva. Testes focados: 20 passaram. O evento 164 foi corrigido de 900 para fator 10, depois reconciliado como MATCHED com data efetiva 09/02/2021 e `NO_FRACTIONAL_RESIDUE`, apos backup v3 e preflight sem posicao historica. Snapshot maintenance: 520 invalidos/reconstruidos e 1 cache invalidado. Imagem backend `sha256:8208c72fab61ca73e184b129b82e1889b35ebdf187c8baae0704603016a815a0`, commit `6816a418b79bea29402cd91576414ff17ad7c806`; `/health` OK, Alembic head, stack ativa. Estado: 3 MATCHED, 3 CONFLICT e 119 UNRECONCILED. Proximo: triagem individual de fatores/labels BRAPI, datas efetivas, pares cross-provider e eventos B3 sem correspondencia; sem promover em lote.

## Triagem de eventos nao quantitativos - 19/10/2026

A leitura do catalogo identificou cinco eventos BRAPI gravados incorretamente como bonificacao apesar dos labels `INCORPORACAO`, `CIS RED CAP` ou `RESG TOTAL RV`: ALOS3 (ID 6), BBDC3 (19), ITSA4 (64), PETZ3 (97) e SANB11 (111). Todos carregam fator bruto 100, sem regra segura de conversao quantitativa. B3 confirma diretamente a cisao BBDC3 e a incorporacao PETZ3, com ISINs de ativos emitidos; nao sao bonificacoes simples. Para ALOS3, ITSA4 e SANB11 nao foi obtida evidenca oficial individual suficiente nesta rodada.

Os cinco permanecem `UNRECONCILED` e fora da projecao; nenhuma escrita foi feita. O zero de candidatos exatos cross-provider nao autoriza reconciliar. Proximo trabalho depende de contrato de dominio para incorporacao/cisao/resgate, incluindo destino, relacao de conversao, data efetiva e alocacao de custo. Issue #370 segue limitada aos conflitos materiais AMOB3/KLBN11.

Contrato proposto para eventos corporativos complexos: `docs/CORPORATE_EVENT_COMPLEX_ACTIONS_DESIGN.md`. O motor atual n�o projeta incorpora��o/cis�o/resgate; `corporate_events` tem apenas um destino e `ticker_change_processor` � um fluxo distinto, portfolio-scoped, que pode criar transa��es sint�ticas durante importa��o. Proposta registra requisito de pernas multiativo, convers�o, aloca��o conservativa de custo e evid�ncia/data efetiva; resgates monet�rios ficam em contrato separado. Nenhuma migration, escrita de banco ou mudan�a de runtime foi feita. Cinco eventos BRAPI mal tipados continuam fail-closed. Issues consultadas: #129 fechada ap�s converg�ncia do motor, #247 fechada ap�s auditoria arquitetural, #370 aberta apenas para evid�ncia de liquida��o KLBN11.

Implementacao parcial do contrato de eventos complexos: `corporate_action_engine.py` agora define `ComplexCorporateActionKind`, `B3ComplexCorporateActionCandidate` e `normalize_b3_complex_corporate_action_candidates`. A classificacao B3 e read-only/in-memory, exige ISIN de origem e data lastDatePrior; incorporacao/cisao exigem ISIN(s) de destino. Linhas de outra classe sao filtradas, identidades sao deterministicas e o candidato explicita `projectable=false`, `quantity_factor=None`, `effective_date=None`. Nenhuma persistencia, reconciliacao, projecao, migration, teste ou alteracao de banco ocorreu. `compileall` e `git diff --check` passaram. Proxima etapa: pernas persistidas multiativo e projetor puro de transformacao sem caixa.

Publicacao do classificador parcial na imagem de testes: commit `2e8b36bdb0cd4d534c4b61b58fa06d7f64e43754`, imagem `sha256:4e129ab9b32319c193ee9655cd43432b4bd400288f4c734fc504c0e377134cb7`. Backend healthy, banco/Redis OK, Alembic head e novo DTO importado. Frontend/tunnel preservados; `/ready=503`, sem novo evento de certificacao. Nenhuma escrita financeira ou teste foi feito.
