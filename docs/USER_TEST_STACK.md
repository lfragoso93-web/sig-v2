# ARQUIVO HISTORICO — stack isolada de testes de usuarios

> Este procedimento foi substituido em 18/10/2026. Nao iniciar, atualizar ou
> reconectar `sgi-usertest`. A validacao com usuarios usa exclusivamente a
> imagem da stack `sig-v2` servida pelo Cloudflare Tunnel; consulte
> `docs/USER_VALIDATION_RUNBOOK.md`. Os registros abaixo sao historicos.

Atualizado em 17/10/2026.

## Objetivo e fronteiras

`docker-compose.usertest.yml` cria a stack Compose `sgi-usertest` para manter o
checkout atual disponivel a testes assistidos sem substituir o runtime que usa
dados reais. Ela usa banco e artefatos proprios, portas locais e a identidade
`ENVIRONMENT=testing`, sem referencia de dataset real nem tokens de providers.
O frontend fica acessivel em `http://127.0.0.1:18080`; o backend, banco e Redis
nao publicam portas no host. A configuracao nao carrega o `.env` do projeto.

A stack nao recebe copia do banco real. O entrypoint cria a conta SuperAdmin
padrao da aplicacao; nao ha fixture de carteira/posicoes carregada. Essa conta
serve para administracao local do SGI e para as rotas restritas ao SuperAdmin.
Jornadas assistidas devem usar contas e fixtures sinteticas aprovadas, sem
importar extratos, CSVs, snapshots ou posicoes reais. `GET /health` informa
saude do servico; `/ready` continua fail-closed e nao e criterio para liberar
este ambiente de testes. Essa separacao remove a recertificacao real como etapa
de cada iteracao de desenvolvimento, preservando a promocao operacional
separada para uso de dados reais.

## Atualizar a imagem de testes

No PowerShell, a partir da raiz do repositorio:

```powershell
$env:APP_COMMIT_SHA = (git rev-parse HEAD).Trim()
docker compose -p sgi-usertest -f docker-compose.yml -f docker-compose.usertest.yml config --quiet
docker compose -p sgi-usertest -f docker-compose.yml -f docker-compose.usertest.yml up -d --build
```

Repetir `up -d --build` apos cada alteracao que deva aparecer no ambiente de
testes. Nao incluir `docker-compose.prod.yml` ou `docker-compose.oci.yml` neste
comando. A tag das imagens e o volume do banco ficam prefixados pelo projeto
`sgi-usertest`; nao apontar essa stack ao projeto `sig-v2`.

Para confirmar o estado:

```powershell
docker compose -p sgi-usertest -f docker-compose.yml -f docker-compose.usertest.yml ps
docker compose -p sgi-usertest -f docker-compose.yml -f docker-compose.usertest.yml logs --tail 100 backend
Invoke-RestMethod http://127.0.0.1:18080/health
```

Confira no backend `APP_BRANCH=stable-15jun`, `APP_COMMIT_SHA` igual ao SHA base,
`ENVIRONMENT=testing`, `REAL_DATASET_REFERENCE` vazio, migration de runtime
esperada e `BRAPI_TOKEN`/`QUOTES_PROVIDER_TOKEN` vazios. A stack principal nao
deve ser reiniciada para atualizar esta imagem.

Quando o working tree estiver sujo, `APP_COMMIT_SHA` identifica somente o SHA
base e nao representa por si so todo o conteudo incorporado na imagem. Registre
esse fato e os digests efetivos; tal imagem e apropriada para teste assistido,
mas nao constitui identidade reproduzivel ou certificavel para dados reais.

## Parar a stack

Use `docker compose -p sgi-usertest -f docker-compose.yml -f docker-compose.usertest.yml stop`
para interromper os servicos sem remover o banco ou os artefatos. Nao use
`down -v` nem remova seus volumes como parte da rotina de atualizacao.

## Estado da implantacao atual — 17/10/2026

Stack reconstruida em 17/10/2026 para incluir a calculadora de rendimentos da
Issue #359 no checkout base `5c4ad3906475316294196a826ff140cb3e4bf950`.
`config --quiet` passou; os containers backend, PostgreSQL e Redis estao
saudaveis; Alembic esta em `20261016_corp_ev_effective_date`; `/health` interno
retorna 200 com Postgres/Redis ok; o frontend em `127.0.0.1:18080` retorna 200.
A rota `/carteira/ferramentas/rendimentos` e o asset JS da aplicacao retornam
200. `npm run typecheck`, build de producao e os quatro testes focados da
calculadora passaram. A verificacao visual desktop/mobile ficou pendente: nao
havia navegador integrado disponivel.
A porta publica extra herdada do Compose base foi removida com `!override`; a
unica porta publicada pela stack e `127.0.0.1:18080`. Os volumes criados sao
`sgi-usertest_postgres_data` e `sgi-usertest_usertest_artifacts`.

Identidade observada: `ENVIRONMENT=testing`, `APP_BRANCH=stable-15jun`,
`APP_COMMIT_SHA` aponta para o SHA base acima, dataset vazio e tokens de
providers vazios. A imagem inclui alteracoes locais nao commitadas; portanto o
SHA informado nao identifica sozinho o conteudo integral e a imagem nao e
certificavel para dados reais. `/ready` responde 503
com `runtime_identity_error`, como esperado para esta identidade de testes sem
certificacao de dados reais; nao e gate para testes assistidos neste projeto.
As imagens locais foram criadas como `sgi-usertest-backend:latest`
(`sha256:b39497dacb281c3270932afb97f144206588171be34f8eaf040fb40e5c6d7e2d`)
e `sgi-usertest-frontend:latest`
(`sha256:4e556c1db342722d7ae3ebbb768af6dd7ab21bec56d0d3cd4567922461930eaf`).
O projeto principal `sig-v2` permaneceu parado e sem alteracoes; banco e volume
da stack de teste foram preservados.

Auditoria read-only da #355 em 17/10/2026 confirmou o ambiente de testes
(`ENVIRONMENT=testing`, branch `stable-15jun`, sem dataset real e Alembic em
`20261016_corp_ev_effective_date`). A tabela de transacoes estava vazia: nao ha
massa de Renda Fixa sintetica para avaliar cobertura ou backfill. Nenhuma linha
foi gravada pela auditoria.


## Atualizacao da imagem - contratos de Renda Fixa #355 - 17/10/2026

Rebuild atualizado apos a implementacao inicial e correcao de relacionamento
ORM. A stack usa `RUNTIME_MIGRATION_TARGET=head` via `docker-compose.usertest.yml`;
o entrypoint mantem `20261016_corp_ev_effective_date` como default fora da
stack de testes. `alembic current` confirmou `20261017_fixed_income_contracts`.

- Backend: `sha256:ea13c260964426decf22c5f2716cecb20ebae30c88bcaf77ff3ec7e455aed019`
- Frontend: `sha256:cbf94cef0431ed1b0270db52d82f4191309e0b049fe36d972054946fd68a6ce5`
- Identidade: `ENVIRONMENT=testing`, branch `stable-15jun`, SHA base
  `5c4ad3906475316294196a826ff140cb3e4bf950`, sem dataset real.
- Estado: backend, PostgreSQL e Redis saudaveis; frontend publicado em
  `127.0.0.1:18080`; `/health=200`, `/ready=503` por identidade sintetica sem
  certificacao real. Rota da API de contratos aparece na OpenAPI.
- Testes: 18 focados passaram sem avisos ORM. Migration foi aplicada; teste
  PostgreSQL rollback-only rejeitou associacao contrato/carteira cruzada e
  confirmou contagens zero para carteiras, transacoes e contratos apos rollback.
- Nenhum backfill foi feito. Nenhum dado de carteira permaneceu no teste. A
  stack principal `sig-v2` nao foi alvo de rebuild ou migracao.

O SHA e apenas a base do checkout; ha alteracoes locais nao commitadas, portanto
estes digests servem para testes assistidos e nao identificam uma release
reproduzivel ou certificada para dados reais.


## Atualizacao da imagem — integracao do formulario #355 — 17/10/2026

Imagens reconstruidas e aplicadas a stack isolada `sgi-usertest` apos recuperacao do BuildKit. O container em execucao corresponde aos IDs abaixo; o checkout ainda contem alteracoes locais nao commitadas, portanto esta imagem serve para testes assistidos e nao e release reproduzivel nem certificacao de dados reais.

- Backend: `sha256:1c7d5ea1b13721e3fa9d0f6bdee0147231ec0fe1c98a479a92af868c638b0ef9`
- Frontend: `sha256:e27c6a1e6d6b2270ce607d57aedc2818fc8e4ff5189b8a528860cb761c3fdd10`
- Alembic: `20261017_fixed_income_contracts (head)`.
- Estado: backend, PostgreSQL e Redis saudaveis; frontend publicado em `127.0.0.1:18080`; `/health=200`, `/ready=503` para identidade sintetica sem certificacao real.
- Validacao: quatro testes backend focados passaram; 16 testes frontend focados e typecheck passaram. O PostgreSQL de testes permaneceu com zero transacoes e zero contratos.
- Dados/escopo: sem backfill ou gravacoes financeiras; a stack principal `sig-v2` nao foi atualizada nem migrada. Nao houve certificacao real.


## CSV de contratos - imagens atualizadas - 18/10/2026

- Backend image ID: `sha256:1495e3127f0b938d7b6ac3a2152eb3bb5ed01c94311a371b6cbcb020cb98f776`
- Frontend image ID: `sha256:42106beaf3428e1ed4040a41f98e8446a3cd36d68c30c337b7e8c16b1f56bcae`
- Containers backend/frontend correspondem aos image IDs acima; imagem de teste construida a partir de uma arvore com alteracoes locais nao commitadas. `APP_COMMIT_SHA` registra `5c4ad3906475316294196a826ff140cb3e4bf950`, somente como base.
- Runtime: backend, PostgreSQL e Redis saudaveis; Alembic `20261017_fixed_income_contracts (head)`; `/health=200`; frontend `127.0.0.1:18080=200`; export CSV autenticado exposto no OpenAPI, acesso sem credencial retorna 401; `/ready=503` e esperado sem dataset/certificacao real.
- Testes na imagem: 82 testes backend CSV e fixture sintetico passaram. No host: 7 testes frontend do modal, `npm run typecheck` e build frontend passaram.
- Estado de dados: zero transacoes e zero contratos na base de teste apos validacao. Sem backfill. Stack principal `sig-v2` nao foi reconstruida nem migrada. Estas imagens nao sao certificacao para dados reais.

## Hierarquia do formulario de Renda Fixa - 18/10/2026

A imagem frontend foi atualizada para apresentar tipo de produto antes do
indexador, sugerir tratamento isento nos produtos com isencao usual e preservar
uma escolha fiscal manual durante a troca de produto. A sugestao nao e
calculo de IRPF. Validacao: 14 testes focados do modal passaram, typecheck e
build Docker passaram. Frontend respondeu 200 em `127.0.0.1:18080`; backend
`/health=200`, `/ready=503` esperado para identidade sintetica. Alembic segue
`20261017_fixed_income_contracts (head)`. Banco/Redis e volumes foram
preservados; stack principal nao foi tocada.

- Backend: `sha256:1495e3127f0b938d7b6ac3a2152eb3bb5ed01c94311a371b6cbcb020cb98f776` (sem alteracao neste bloco).
- Frontend: `sha256:9cedcea08da45ee3d07055fd98bc45e9d5c5e586d681f44b4bccff1f7c368b8d`.
- Conteudo construido de working tree com alteracoes locais; SHA base nao e identidade integral da imagem e nao ha certificacao real.

## Tentativa de associacao transparente - 18/10/2026

Typecheck do frontend passou e a etapa de build frontend compilou. O build
backend/frontend combinado falhou durante a exportacao/unpack backend com EOF;
na consulta seguinte Docker Desktop reportou que a engine WSL nao iniciava
(`0xc00000fd`). Nao foi possivel verificar IDs finais nem estado dos containers
apos o erro. A imagem deste bloco nao esta confirmada como implantada; recuperar
Docker e auditar `sgi-usertest` antes de nova tentativa. Nenhum volume foi
removido intencionalmente e a stack principal nao foi alvo do comando.

### Recuperacao e runtime confirmado - 18/10/2026

Docker voltou a responder sem reinicio manual do engine. Rebuild concluido e
servicos backend/frontend recriados na stack `sgi-usertest`; PostgreSQL, Redis
e volumes preservados.

- Backend em execucao: `sha256:598f73a8fc949493e25a919b4449992b6e40f5449b1bbd9ba6ba11ec710b929d`.
- Frontend em execucao: `sha256:7224856e167182dab7db87f49c69a92a2ba88bb1d4d445b5eace5666d8b57169`.
- Alembic: `20261017_fixed_income_contracts (head)`; `/health=200`; `/ready=503` esperado sem identidade de dados reais; OpenAPI contem a rota de contratos; `127.0.0.1:18080=200`.
- Typecheck passou. Nao foram adicionados ou executados testes. Imagens incluem working tree alterado e nao constituem release reproduzivel ou certificacao de dados reais.

### Validacao automatica e imagem atualizada - 18/10/2026

A regressao backend confirma reuso somente para termos equivalentes na mesma
carteira; 12 testes de `test_fixed_income_contract_service.py` passaram com
SQLite em memoria. `npx tsc --noEmit` passou. O teste de prefill frontend foi
adicionado, mas Vitest ficou sem progresso mesmo com permissao elevada e foi
interrompido sem resultado. O browser integrado retornou lista vazia; nao houve
validacao visual desktop/mobile.

O rebuild e recreate foram concluidos para backend/frontend. Identidade
registrada em `APP_COMMIT_SHA=5c4ad3906475316294196a826ff140cb3e4bf950`, que e
somente o HEAD base: a imagem inclui working tree com mudancas locais e nao e
release reproduzivel nem certificacao para dados reais.

- Backend em execucao: `sha256:71bd2f62c3b11cfa456cc2d9b1dd8d4aceb49460fac6067e90e196de4a59348f`.
- Frontend em execucao: `sha256:75ca18ef0a364722eb540f4e20634fd09eca3e318c6a4c5dbcf83090476c5865`.
- Backend, PostgreSQL e Redis healthy; Alembic `20261017_fixed_income_contracts (head)`; `/health=200` consultado dentro do backend; `/ready=503` esperado para identidade sintetica sem certificacao de dados reais; frontend `127.0.0.1:18080=200`.
- PostgreSQL, Redis e volumes nao foram recriados. Nenhuma transacao/contrato foi inserido pela validacao; stack principal `sig-v2` nao foi alvo.

### Isolamento de carteira - 18/10/2026

Adicionado teste ao writer canonico: mesmo nome e termos em duas carteiras
produzem contratos distintos, preservando o ownership. A suite focada passou
com 13 testes em SQLite em memoria. Nenhum dado financeiro real ou persistente
foi usado.

Imagem backend apos regressao de escopo por carteira:
`sha256:700171073da7ac0fff016e3f64627f19dc0a72ff0aaf6ea90667c63d367e7708`.
Container corresponde a esse image ID e esta healthy. A imagem frontend permaneceu
`sha256:7224856e167182dab7db87f49c69a92a2ba88bb1d4d445b5eace5666d8b57169`.
Verificacao final: Alembic `20261017_fixed_income_contracts (head)`, `/health=200`,
`/ready=503`, interface `127.0.0.1:18080=200`, `transactions=0` e
`fixed_income_contracts=0`. PostgreSQL e Redis permaneceram nos containers
existentes, sem recriacao ou alteracao de volumes.

### Normalizacao de nome/emissor aplicada - 18/10/2026

A imagem backend final apos a normalizacao esta ativa com digest
`sha256:93053a6fb003b46b84beaea359235033deb051f4cde3654904e436aaef1cba58`.
Frontend permaneceu em
`sha256:7224856e167182dab7db87f49c69a92a2ba88bb1d4d445b5eace5666d8b57169`.
Backend/DB/Redis estao saudaveis; Alembic em head, `/health=200`,
`/ready=503`, frontend 200 e contagens persistentes zero para transacoes e
contratos. Apenas backend foi recriado; DB, Redis, volumes e frontend foram
preservados.

### Stack completa atualizada para testes de usuarios - 18/10/2026

Backend e frontend foram reconstruidos a partir do working tree atual e estao
aplicados em `sgi-usertest`:

- Backend: `sha256:93053a6fb003b46b84beaea359235033deb051f4cde3654904e436aaef1cba58`.
- Frontend: `sha256:86b034acfd1ae248af234f6dd97c926c9f74f57ecb8fed5e40d87a9d3a74e3ea`.
- Fonte base registrada: `stable-15jun`, HEAD
  `5c4ad3906475316294196a826ff140cb3e4bf950`; a imagem inclui mudancas locais
  nao commitadas e nao e uma release reproduzivel.
- Backend, PostgreSQL e Redis healthy; Alembic
  `20261017_fixed_income_contracts (head)`; `/health=200`; `/ready=503` esperado
  para identidade `testing` sem dataset ou evento de certificacao real.
- Frontend `127.0.0.1:18080=200`; bundle JS servido com HTTP 200. OpenAPI inclui
  rotas de contratos de Renda Fixa e exportacao CSV.
- `transactions=0`, `fixed_income_contracts=0`,
  `real_data_certification_events=0`. Nenhum volume ou banco foi removido; DB,
  Redis e volumes foram preservados.
- Typecheck do frontend passou anteriormente; teste Vitest de prefill ficou
  sem resultado por travamento, e validacao visual integrada nao foi possivel
  por ausencia de browser conectado. A stack esta pronta para testes assistidos
  por usuarios; nao e certificacao para dados reais.

A stack principal `sig-v2` nao foi atualizada. Esta acao aplicou imagens no
Docker local; nao publicou tags em registry nem criou release/PR.
