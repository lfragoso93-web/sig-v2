# Certificação funcional de carteira — PORTFOLIO-TEST-READY

## Objetivo

Este documento define o gate funcional anterior ao uso de carteiras e dados reais no SGI v2.

A certificação deve provar, com dados sintéticos e reproduzíveis, que o fluxo financeiro ponta a ponta permanece consistente antes de avançar para os gates reais #226, #216, #158 e #227.

Issue canônica: #303.

## Separação de ambientes

### Desenvolvimento e certificação pesada — LOCAL

Ambiente oficial:

- Windows;
- PowerShell;
- Docker Desktop;
- branch `stable-15jun`.

Devem ocorrer localmente:

- desenvolvimento e correções;
- builds;
- migrations de teste;
- pytest e qualidade backend;
- testes/lint/build frontend;
- bootstrap com dados permitidos;
- criação da carteira sintética;
- importação CSV sintética;
- reconciliação financeira detalhada;
- testes de restart, cache e persistência;
- geração das evidências do gate.

### Homologação real — OCI Free Tier

A OCI não é ambiente de desenvolvimento.

Ela recebe somente um SHA já aprovado no gate local e é usada para:

- deploy do SHA certificado;
- migrations necessárias;
- smoke reduzido;
- validação de PostgreSQL, Redis e volumes;
- restart/reboot;
- Cloudflare/rede;
- CPU, memória e disco;
- integrações externas autorizadas;
- homologação operacional final.

Falhas de código encontradas na OCI devem voltar para o ciclo local: diagnosticar → reproduzir localmente → corrigir → testar → commit → push → atualizar OCI → retestar.

## Readiness

Durante toda esta certificação:

- `test_ready=true` permite usuário, carteira e dados fictícios/descartáveis;
- `ready_for_real_data=false` permanece obrigatório;
- nenhuma flag deve ser forçada para contornar #226/#216/#158/#227;
- nenhum seed real de Proventos é autorizado por este documento;
- nenhum CSV real é autorizado por este documento.

## Estado da certificacao #303

Baseline atual publicado em `stable-15jun`:

- `b852e9ccdfbf48500b763c98bbcfa3ce6b1ad3b8`: contrato do fixture sintetico
  multiclasse explicita classes, taxas, provento, ativo sem provento, venda
  parcial, venda total e recompra;
- `47026d4faddee55398ddb00b8e2dc08c601fb979`: upload CSV sintetico em
  `dry_run=True` validado como read-only;
- `bc38e6de8da657b09e9e9e6321516be8dd49950b`: importacao efetiva CSV
  sintetica validada com commit unico;
- `026421109fa959ba578c942a6bdd883954eabc98`: repeticao do CSV sintetico
  validada como duplicidade/idempotencia;
- `aa2926cf11231c252a4ea85f60af94e8cc52ed1c`: linha invalida derivada do
  fixture bloqueia persistencia;
- `db81a3ae40445856bfb1982bfaabb6f459c69e17`: importacao real agenda rebuild
  de snapshots em background;
- `e2487fd6809fc683427c9b59efc711469687b150`: linhas `RENDA_FIXA` e
  `TESOURO_DIRETO` preparam `fixed_income_investments` antes do commit;
- `310db2420a1afb3f1ea896fd5fcaea214b36e128`: Rentabilidade reconciliada com
  `TESOURO_DIRETO` e `RENDA_FIXA` sem TWR dedicado, como
  `partial_by_design`;
- `39d2ee8c0fd64fa82aa264e8ad88343431580b3e`: classes fiscais comuns do
  fixture mapeadas para a matriz sintetica de IRPF;
- `ad9b027a9087173e270117741ecebea4cd4279ab`: modal de importacao CSV
  bloqueia confirmacao apos dry-run com erro, sem importacao real, `onSuccess`
  ou invalidacao de cache;
- `712dad454ab4bcf0a06d1950458bd0f69d280a99`: cache Redis validado como
  best-effort/fail-open quando Redis esta indisponivel;
- `883e6dcbcfee0f344baf34065fb39c46775ef9c4`: `/health` mantem Redis
  indisponivel como sinal informativo/non-blocking, enquanto Postgres segue
  como dependencia degradante;
- `11ab59339fe30ad6c1c1f177841045680976a8d4`: Compose local validado por
  contrato estrutural com Postgres persistente, healthchecks/dependencias
  `service_healthy` e Redis efemero como cache.

Esses blocos avancam os itens B, C, D, E, F e G em nivel dirigido. O marco
`PORTFOLIO-TEST-READY` ainda nao esta aprovado: permanecem pendentes a
certificacao local integrada, UI ponta a ponta alem do modal CSV, resiliencia/restart,
persistencia/volumes e a selecao de um SHA final para homologacao OCI.

Estimativa operacional apos `883e6dcbcfee0f344baf34065fb39c46775ef9c4`:

- concluido em nivel dirigido: dataset sintetico, reconciliacao independente,
  CSV dry-run/import/reexecucao/invalidos/rebuild agendado, Tesouro/Renda Fixa
  fail-closed parcial, matriz IRPF, modal CSV critico e Redis fail-open;
- pendente para aprovar o gate: uma bateria integrada local com Compose,
  restart backend/Redis/Compose com containers reais, prova operacional de
  persistencia PostgreSQL/volumes, verificacao de snapshots/cache apos restart,
  smoke UI ponta a ponta alem do modal CSV e registro do SHA final aprovado.

Evidencia local adicional:

- `docker compose config --quiet` passou apos corrigir o `.env` local ignorado
  pelo Git para usar `;` como separador Windows de `COMPOSE_FILE`;
- servicos efetivos renderizados: `redis`, `db`, `backend`, `frontend`,
  `cloudflared`;
- volume efetivo renderizado: `postgres_data`.

Evidencia operacional local em containers:

- backend reconstruido e recriado com runtime `APP_COMMIT_SHA` =
  `8decdae25f7d5a7a8fa4a64a90e6d01543c2d708`;
- `docker compose -f docker-compose.yml ps` mostrou `backend`, `db` e `redis`
  `healthy`;
- `/health` retornou `status=ok`, `postgres=ok`, `redis=ok` e
  `ready_for_real_data=false`;
- `pg_isready -U sgi -d sgi` retornou accepting connections;
- `redis-cli ping` retornou `PONG`;
- `alembic current` retornou `20260820_dividend_occurrence (head)`.

Evidencia operacional de restart controlado:

- `docker compose -f docker-compose.yml restart redis` concluiu e Redis voltou
  `healthy`;
- apos restart Redis, `/health` permaneceu `status=ok`, `postgres=ok` e
  `redis=ok`;
- `docker compose -f docker-compose.yml restart backend` concluiu, executou o
  entrypoint com migrations runtime-safe e recriou o servidor;
- apos restart backend, `backend`, `db` e `redis` permaneceram `healthy`;
- runtime `APP_COMMIT_SHA` permaneceu
  `8decdae25f7d5a7a8fa4a64a90e6d01543c2d708`;
- `alembic current` permaneceu `20260820_dividend_occurrence (head)`.

Evidencia operacional de persistencia PostgreSQL/volume:

- criada tabela sintetica temporaria `portfolio_test_ready_volume_probe` com
  marcador `synthetic-volume-probe`;
- `docker compose -f docker-compose.yml restart db` concluiu sem remover
  volumes;
- apos restart, `db` voltou `healthy`, backend permaneceu `healthy` e
  `/health` retornou `status=ok`, `postgres=ok`, `redis=ok`;
- marcador `synthetic-volume-probe` permaneceu legivel apos restart do
  Postgres, comprovando persistencia no volume `postgres_data`;
- tabela sintetica temporaria removida ao final da prova;
- `alembic current` permaneceu `20260820_dividend_occurrence (head)`.

Evidencia operacional de restart completo do Compose:

- `docker compose -f docker-compose.yml restart` reiniciou `redis`, `backend`,
  `db` e `frontend` sem remover volumes;
- apos estabilizacao, `backend`, `db` e `redis` voltaram `healthy`, e
  `frontend` voltou a responder HTTP;
- `/health` retornou `status=ok`, `postgres=ok`, `redis=ok` e
  `ready_for_real_data=false`;
- runtime `APP_COMMIT_SHA` permaneceu
  `8decdae25f7d5a7a8fa4a64a90e6d01543c2d708`;
- `alembic current` permaneceu `20260820_dividend_occurrence (head)`;
- `pg_isready -U sgi -d sgi` retornou accepting connections;
- `redis-cli ping` retornou `PONG`;
- `http://localhost/` retornou HTTP 200.

Evidencia operacional de snapshots/cache apos restart:

- apos restart completo, `portfolio_snapshots` e
  `portfolio_class_snapshots` permaneceram presentes no schema PostgreSQL;
- Redis aceitou chave sintetica temporaria `portfolio-test-ready-cache-probe`,
  retornou `synthetic-cache-probe`, removeu a chave e confirmou `exists=0`;
- durante a prova, `/health` permaneceu `status=ok`, `postgres=ok`,
  `redis=ok` e `ready_for_real_data=false`.

## Ordem obrigatória

### A. Baseline local

1. confirmar diretório e repositório;
2. confirmar `stable-15jun`;
3. `git fetch origin`;
4. comparar HEAD local, `origin/stable-15jun` e `origin/main`;
5. reconciliar a divergência de branch sem perder commits da `stable-15jun`;
6. confirmar working tree limpa;
7. confirmar Issues/PRs relevantes;
8. confirmar Docker Desktop e serviços Compose;
9. validar Alembic/migration head e drift gate;
10. executar qualidade proporcional ao HEAD;
11. validar backend, frontend e smoke local;
12. validar bootstrap somente nos estágios permitidos.

### B. Dataset sintético canônico

Criar um dataset determinístico e versionável para uma carteira multiclasse.

Fixture canônica atual:

- `backend/tests/fixtures/portfolio_synthetic_certification_v1.json`;
- schema `portfolio-synthetic-certification.v1`;
- `test_ready=true`, `ready_for_real_data=false` e `real_data_allowed=false`;
- reconciliada por `backend/tests/test_portfolio_synthetic_certification_fixture.py`.

Cobrir, quando suportado pelo contrato corrente:

- Ação;
- FII;
- ETF;
- BDR;
- Criptomoeda elegível;
- Tesouro Direto;
- Renda Fixa.

Casos mínimos:

- compra única;
- duas ou mais compras em preços/datas diferentes;
- venda parcial;
- venda total;
- recompra depois de zerar a posição;
- taxas;
- ativo com Proventos;
- ativo sem Proventos;
- posição constante com variação de preço;
- cobertura completa e cobertura ausente/incompleta.

O dataset não deve depender de dados pessoais reais.

### C. Reconciliação financeira independente

Para cada caso, calcular expectativas de maneira independente da API e comparar com o SGI.

Validar no mínimo:

- quantidade;
- custo/preço médio;
- custo remanescente após venda;
- resultado realizado;
- total investido;
- valor atual;
- resultado em aberto;
- Proventos conforme contrato canônico;
- patrimônio;
- distribuição por classe;
- snapshots;
- TWR/rentabilidade onde disponível;
- IRPF para operações cobertas.

Tolerância monetária padrão: R$ 0,01, salvo contrato existente mais preciso.

Nenhuma ausência de cobertura pode ser transformada silenciosamente em zero ou retorno simples.

A fixture `portfolio-synthetic-certification.v1` calcula quantidade, custo
remanescente, resultado realizado, valor de mercado, proventos sintéticos,
resultado em aberto e resultado total de forma independente dos serviços da API.
Ela usa FIFO para custo liberado em vendas e tolerância monetária de centavo.

### D. CSV sintético

Validar:

- dry-run;
- erros e warnings;
- normalização/resolução de ticker;
- importação efetiva;
- invalidação de cache;
- rebuild de snapshots;
- estado imediatamente após a resposta HTTP;
- estado depois do rebuild;
- comportamento em reexecução;
- anti-duplicidade/idempotência conforme o contrato;
- venda parcial/total e recompra via histórico importado.

Contrato de reexecução atual:

- uma linha com mesma carteira, ticker, classe, operação, quantidade, preço,
  data, taxas e moeda é tratada como duplicada;
- duplicatas idênticas retornam `status="skipped"` e incrementam
  `skipped_count`;
- quando a reexecução não importa nenhuma transação nova, não há commit nem
  invalidação de cache.

### E. Tesouro Direto — marcação a mercado + TWR

A rentabilidade oficial de Tesouro Direto deve refletir marcação a mercado, não apenas a taxa contratada ou a curva teórica.

Contrato esperado:

- patrimônio diário = quantidade econômica × PU de mercado persistido do título na data;
- variação de PU com posição constante é retorno de mercado;
- compras/aportes são fluxos externos e não lucro;
- vendas/resgates são fluxos externos e não perda;
- cupons e amortizações devem ser segregados para não haver dupla contagem entre patrimônio e caixa;
- vencimento deve encerrar a posição pelo valor efetivamente liquidado, preservando o retorno acumulado;
- taxa contratada/curva pode permanecer como informação de contratação/accrual onde aplicável, mas não substitui o PU de mercado na rentabilidade oficial;
- falta de PU diário deve publicar indisponibilidade explícita/fail-closed;
- provider externo não pode ser chamado durante cálculo/read path para preencher lacunas.

Casos mínimos independentes:

1. posição constante + queda de PU => retorno negativo, mesmo com taxa contratada positiva;
2. posição constante + alta de PU => retorno positivo;
3. compra no meio da série não vira retorno do dia;
4. venda parcial não distorce o TWR;
5. cupom/amortização não é contado duas vezes;
6. vencimento/resgate zera a posição e preserva a cadeia anterior;
7. lacuna de PU interrompe/publica indisponibilidade conforme contrato.

Antes da integração produtiva da #149, confirmar qual histórico oficial persistido e qual campo de PU são a fonte canônica da cadeia diária.

### F. Renda Fixa — consistência operacional

Validar explicitamente:

- coerência entre transações e `fixed_income_investments`;
- comportamento se o side-effect de upsert falhar;
- ausência de estado parcialmente consistente silencioso;
- invalidação de cache;
- cálculo por indexador e séries persistidas;
- fail-closed quando a cadeia TWR dedicada não tiver cobertura suficiente.

### G. UI ponta a ponta

Validar:

- login e seleção/criação de carteira;
- Transações;
- Patrimônio;
- Posições;
- Rentabilidade;
- Proventos;
- IRPF;
- filtros/períodos relevantes;
- estados vazios/indisponíveis coerentes;
- ausência de chamadas inesperadas a providers em read paths financeiros.

### H. Resiliência local

Validar:

- restart do backend;
- Redis indisponível/fail-open;
- restart completo do Compose;
- persistência PostgreSQL/volumes;
- caches e snapshots após restart;
- Alembic ainda no head esperado.

## Bugs e gaps encontrados

Cada bug deve virar Issue pequena própria com:

- comportamento esperado;
- comportamento observado;
- passos de reprodução;
- SHA;
- ambiente;
- severidade;
- evidência;
- critério de aceite.

Não esconder bugs dentro da #303 e não misturar várias correções não relacionadas no mesmo commit.

## Critério PORTFOLIO-TEST-READY

O gate local só é aprovado quando:

- dataset sintético reproduzível estiver documentado;
- principais números financeiros estiverem reconciliados;
- Tesouro tiver semântica explícita de marcação a mercado e fluxo;
- Renda Fixa não puder ficar parcialmente consistente silenciosamente;
- CSV e rebuild estiverem validados;
- UI crítica estiver validada;
- restart/persistência estiverem aprovados;
- blockers encontrados estiverem corrigidos;
- documentação viva refletir o resultado;
- existir SHA exato da `stable-15jun` aprovado para homologação OCI.

## Próxima etapa após aprovação

Após `PORTFOLIO-TEST-READY`:

1. executar somente então os gates reais #226 → #216 → #158 → #227;
2. selecionar um SHA exato já certificado localmente;
3. atualizar OCI para esse SHA;
4. realizar homologação reduzida e operacional;
5. qualquer falha de código retorna ao ambiente local.
