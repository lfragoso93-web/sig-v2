# Continuidade de desenvolvimento — SGI v2

> Documento obrigatório para iniciar ou retomar qualquer conversa de desenvolvimento. Atualizado em 31/08/2026.

## Rebaseline pós-merge PR #302 — 01/09/2026

- PR #302 mergeada em `main` em 01/09/2026 pelo commit `7861268a2528d80e8c23dfc55f7b0800402abc6d`.
- `stable-15jun` permanece a branch obrigatória de desenvolvimento, atualmente em `2c9358629b3e5e9206a365ebeac45f9272dfd48e`.
- A diferença esperada entre `origin/main` e `origin/stable-15jun` é apenas o merge commit da #302; novo desenvolvimento deve continuar em `stable-15jun`.
- Issues abertas inventariadas: 18 (#293, #284, #272, #269, #253, #246, #227, #226, #216, #158, #150, #149, #130, #127, #97, #90, #83, #58).
- PRs abertas atuais: nenhuma após triagem dos Dependabot #295, #296, #297, #298, #299, #300 e #301.
- Não abrir PR nova para microblocos; registrar commits pequenos e preparar promoção somente ao fechar macrobloco validado.
- PRs #295, #296, #297, #298, #300 e #301 foram absorvidas integralmente em `stable-15jun` e encerradas.
- PR #299 foi encerrada no formato original; apenas `@vitejs/plugin-react 6.1.1` foi absorvido, enquanto TypeScript 7 permanece bloqueado por incompatibilidade com `typescript-eslint`.

## #149 — TWR dedicado Tesouro/Renda Fixa — 01/09/2026

- Primeiro bloco funcional concluido em `stable-15jun`: `twr_service` ganhou uma cadeia diaria pura para classes com historico dedicado.
- A cadeia reutiliza o calculo canonico de TWR diario e composicao acumulada, segregando aportes/retiradas como fluxo externo e rendimentos/cupom como retorno.
- O contrato e fail-closed: se faltar cobertura diaria dedicada, a linha publica indisponibilidade explicita e os dias seguintes ficam interrompidos, sem fallback para custo, curva nominal, valor sintetico ou provider em runtime.
- Testes sinteticos cobrem variacao patrimonial por PU/preco, aporte neutro, rendimento/cupom, ausencia de cobertura e data duplicada.
- Ainda nao houve integracao produtiva com `PortfolioClassSnapshot`; Tesouro Direto e Renda Fixa continuam sem TWR publicado ate o proximo bloco da #149.

## Contexto permanente

- Repositório: `lfragoso93-web/sig-v2`.
- Branch obrigatória: `stable-15jun`; nunca desenvolver diretamente na `main`.
- Confirmar o HEAD remoto e a árvore limpa antes de cada bloco.
- Dividir macroblocos em commits pequenos, independentes e rastreáveis.
- Antes de alterar, revisar Issue, arquitetura, contratos canônicos, consumidores e legado.
- Ao final informar resumo técnico, impacto arquitetural, arquivos, testes, SHA completo, Issue/documentação e próximo bloco.
- `goals` permanece fora da estabilização corrente e não recebe migration apenas para limpar Alembic.

## Baseline confirmado — 27/08/2026

No início do rebaseline de certificação:

- `stable-15jun`: `a889edb6bbbb78feb7787c21b3439a0b835b73c6`;
- `main`: `3eeca232a8627f4562544739112d1dde82b879fb`;
- PR #292 já promovida para `main`;
- `stable-15jun` avançou após a PR #292 com pequenos blocos de documentação e smoke;
- `test_ready=true`: permitido testar com dados fictícios/descartáveis;
- `ready_for_real_data=false`: usuários, carteiras, CSV, seeds e snapshots reais continuam bloqueados até decisão formal.

Marcos anteriores preservados:

- #247 concluída e promovida pela PR #281;
- bloco final da #269 promovido pela PR #282;
- #268 certificou o primeiro `test_ready=true`;
- #267 consolidou o universo CRIPTO suportado;
- `system-bootstrap.v4` permanece a engine única de bootstrap.

## Estado OCI atual

O OCI está em fase de laboratório/certificação, não mais apenas planejamento.

Evidências já disponíveis:

- compatibilidade ARM64 validada para backend, frontend, PostgreSQL e Redis;
- laboratório OCI descartável preparado e utilizado;
- frontend production build aprovado;
- Cloudflare Tunnel validado como entrada pública sem publicação direta dos serviços internos;
- hostname público retornou HTTP/2 200;
- smoke OCI aprovado;
- PR #291 criou wrapper repetível para validação dos contratos de seed/bootstrap;
- PR #292 endureceu o smoke HTTP descartável;
- contratos validados sem executar seeds reais:
  - FX/Macro/Tesouro: 81 passed, 1 skipped;
  - B3/Asset Bootstrap/System Bootstrap: 70 passed;
  - Proventos: 93 passed, 8 skipped;
- SHA `a889edb6bbbb78feb7787c21b3439a0b835b73c6` garante no smoke que usuário comum recebe `403` em `/api/v1/admin/bootstrap/status`.

Essas validações não promovem `ready_for_real_data`.

## Baseline corrente — 31/08/2026

Estado verificado em `stable-15jun`:

- HEAD local e remoto: `e9e81d20370593419a11f8a941547c8fe0245873`;
- árvore limpa antes da próxima rodada;
- Issues abertas inventariadas: 18;
- gates de dados reais ainda abertos: #227, #158, #216 e #226;
- migração/certificação OCI permanece em #284;
- saneamento de backlog permanece em #293.

Blocos recentes já enviados ao remoto após o rebaseline:

- B3 COTAHIST passou a ser fonte primária do catálogo mínimo B3 e do OHLCV
  histórico certificado;
- BRAPI deixou de criar ativos B3 ausentes do baseline COTAHIST e passou a
  enriquecer apenas ativos B3 já conhecidos;
- `system-bootstrap.v4` ganhou estágio `b3_baseline` antes de `asset_catalog`;
- o fim da janela B3 é sempre derivado do dia atual, sem variável `.env`;
- Proventos foram contraídos para BRAPI autoritativa e Yahoo/yfinance
  fallback-only após ausência real de cobertura;
- persistência de Proventos rejeita linhas normalizadas simultâneas de BRAPI e
  Yahoo no mesmo ativo;
- lógica obsoleta de reconciliação complementar/cross-source via Yahoo foi
  removida da persistência.

Validações sintéticas recentes:

- B3/COTAHIST/catalog/bootstrap: testes unitários e estruturais focados verdes;
- Proventos coletor/persistência/semântica: `42 passed`;
- nenhuma execução real de seed de Proventos, CSV, snapshot, migration física,
  full rebuild real ou `ready_for_real_data=true`.

## CERT-01A — qualidade de aplicação no OCI lab

O entrypoint canônico é `scripts/oci_certification_quality.sh`.

Ele exige branch `stable-15jun`, árvore limpa e pode fixar `SGI_CERT_EXPECTED_SHA`. Executa PostgreSQL 16 temporário, qualidade completa de backend, qualidade completa de frontend, dependency audits e os smokes/contratos OCI existentes sem seed real.

Durante a primeira execução real no lab foram encontrados dois problemas exclusivamente operacionais do wrapper/host, sem evidência de regressão do SGI:

1. BuildKit retornou `forwarding Ping: no such job`; o wrapper passou a validar o daemon e possui uma única tentativa segura com builder clássico como fallback.
2. A suíte backend chegou a `513 passed, 4 skipped` antes de falhar em `test_entrypoint_schema_authority.py` porque o container de certificação montava apenas `backend:/app`; o teste estrutural corretamente esperava `docker-compose.prod.yml` e `docker-compose.oci.yml` na raiz calculada. O wrapper agora monta os três arquivos Compose canônicos read-only nos paths de raiz esperados, sem alterar ou relaxar o teste.

CERT-01A foi aprovado no OCI lab sobre `d7c03078c9b31cfd004e88e321557ddc0f0658fe`: backend `1623 passed, 35 skipped`, `pip-audit` sem vulnerabilidades conhecidas, frontend completo aprovado, contratos de seed/bootstrap aprovados sem seed real, smoke HTTP descartável aprovado, `ready_for_real_data=false` preservado e árvore limpa ao final.

## CERT-01B — segurança no OCI lab

O entrypoint canônico é `scripts/oci_certification_security.sh` e o runbook é `docs/deployment/oci-certification-security.md`.

Na primeira execução real do CERT-01B, o Trivy filesystem encontrou `AVD-DS-0002` HIGH em `frontend/Dockerfile.prod`: runtime Nginx sem `USER` não-root. A análise arquitetural mostrou que esse Dockerfile era também uma duplicação legada do Dockerfile canônico.

Correção estrutural em microblocos:

- `fbf575c3146c45ccee1aa1e272384d7a865ba926` — Dockerfile canônico passa a executar Nginx como usuário `nginx`, mantendo a porta interna 80 por `CAP_NET_BIND_SERVICE` mínima;
- `225baaa9c25e1ea008c37355c682a66c11b449cc` — `docker-compose.prod.yml` converge para o Dockerfile canônico;
- `943f052da046333242f6f8e252b9fde2e1baf546` — remove `frontend/Dockerfile.prod` legado;
- `62a52ec12d71cb11619fdf75282d093ed859d2ed` — backend runtime passa a executar como usuário `app` não-root;
- `6a5a8f224c210454cc31e92b4b23b73a583a685a` — gate valida UID não-root e startup HTTP do frontend;
- `8f3a01e31078ca8db1dbcf143caa2531603e6c15` — smoke preserva exit code e logs do frontend para diagnóstico;
- `4b7bf44a59a17212f1fb0aef174e013c991085af` — smoke isolado passa a resolver `backend` localmente, porque o Nginx canônico exige o upstream no startup mesmo quando o teste solicita apenas `/`.

A reexecução sobre `8f3a01e3...` confirmou `backend uid=1000` e `frontend uid=101`. O frontend caiu somente porque o smoke isolado não possuía DNS/hosts para o upstream `backend`; não houve falha de permissão, bind ou execução não-root. O warning da imagem oficial sobre a diretiva `user` do nginx é esperado quando o master já inicia sem root.

CERT-01B permanece pendente até reexecução integral sobre o HEAD atualizado e reconciliação de CodeQL/Code Scanning, Dependabot Security Alerts e Secret Scanning. Os avisos do Trivy sobre `site-packages`/`npm install` durante license detection são informativos e não constituíram finding de vulnerabilidade.

## Segurança

O bloco final da #269 tratou:

- path injection residual do serviço de backup;
- sanitização de sinks residuais de log;
- hardening da imagem runtime sem pip/setuptools;
- publicação SARIF do Trivy da imagem backend no workflow `Security deep scan`.

Evidências preservadas:

- 1.611 testes backend aprovados e 35 ignorados no bloco final de segurança;
- 105 testes dirigidos dos domínios afetados;
- flake8, mypy, compileall e `import app.main` aprovados;
- CI da PR #282 aprovado;
- CI global posterior aprovou backend, frontend, `pip-audit`, `npm audit`, Gitleaks, Trivy filesystem e Hadolint.

O `Security deep scan` continua semanal/manual. Não presumir execução ou zeragem de alertas externos sem evidência explícita.

## Arquitetura que deve ser preservada

- Runtime financeiro é DB-first; provider não participa de GETs/cálculos financeiros.
- Providers pertencem a bootstrap, ingestão, sincronização ou reconciliação explicitamente autorizados.
- Preços externos são persistidos antes do consumo financeiro.
- Ausência de preço/FX é explícita; não vira zero, preço médio, taxa `1.0` ou fallback silencioso.
- `summary.v2`, `rentabilidade.v2`, projetores de posição/custo e snapshots são contratos canônicos.
- Proventos pertencem ao ativo em `asset_dividends`; direitos por carteira são calculados sob demanda.
- Eventos corporativos pertencem ao ativo em `corporate_events`; transações históricas não são mutadas.
- Não reintroduzir `AppConfig`, `IRPFReport`, `Dividend/dividends`, routers placeholders ou materialização de Proventos por carteira.
- Tesouro/Renda Fixa devem preservar marcação a mercado; evolução de TWR pertence à #149.
- `goals` continua exceção deliberada de Alembic/MetaData até #246 + #57.

## Trabalho corrente — certificação para TESTES integrados

Nenhuma nova funcionalidade deve ser iniciada antes deste gate.

### Etapa 1 — rebaseline de governança

Concluída em 27/08/2026 para README, ROADMAP, CHANGELOG, `DEVELOPMENT_CONTINUITY` e Issues centrais.

### Etapa 2 — bateria completa com dados descartáveis

Validar no lab:

1. backend: pytest, compileall, import `app.main`, lint/type gates e Alembic;
2. frontend: install, lint, typecheck, tests e production build;
3. segurança: audits e scans disponíveis;
4. stack: `/health`, `/ready`, frontend HTTP e Cloudflare;
5. restart e persistência dos volumes;
6. Redis fail-open;
7. migrations em base descartável;
8. controles de SuperAdmin e ausência de exposição indevida.

### Etapa 3 — bootstrap sem contornar gates

- executar somente contratos/testes permitidos;
- não forçar `ready_for_real_data=true`;
- não alterar manualmente estados apenas para passar teste;
- não executar Proventos reais sem autorização vigente da #226;
- não contornar #216/#158;
- falhar fechado quando a arquitetura exigir.

### Etapa 4 — dados reais, somente quando autorizados

Ordem operacional:

1. #226 — duas execuções reais controladas de Proventos;
2. #216 — reconciliar evidências e fechar gate agregado;
3. #158 — importar CSV controlado, reconstruir posições e snapshots;
4. reconciliar patrimônio, rentabilidade, Proventos, Tesouro, Renda Fixa e IRPF;
5. repetir restart/idempotência/falhas;
6. produzir decisão GO / NO-GO;
7. somente então considerar `ready_for_real_data=true`.

## Ordem posterior à primeira certificação

1. #150 — histórico persistido do IBOV: implementação DB-first via COTAHIST concluída; validação real segue bloqueada pelos gates operacionais;
2. #149 — TWR Tesouro/Renda Fixa: base diaria pura concluida; integrar historicos dedicados e snapshots;
3. #272 — dívida física de `corporate_events` em bloco separado;
4. #83 — hardening residual do Backup/Restore administrativo;
5. demais backlog de produto;
6. #246 + #57 — Metas + Análise de Carteira como macroprojeto único.

## PRs Dependabot abertas

Em 01/09/2026, as PRs abertas são #295, #296, #297, #298, #299, #300 e #301, todas de Dependabot contra `main`.

Não mergear automaticamente. Cada atualização deve ser tratada em bloco próprio, com `stable-15jun` sincronizada, instalação determinística, suítes backend/frontend aplicáveis e CI verde antes de promoção.

## Qualidade por macrobloco

Backend:

- pytest;
- compileall;
- import `app.main`;
- flake8/ruff conforme gate vigente;
- mypy;
- Alembic heads/current/check;
- fresh DB migration gate.

Frontend:

- `npm ci`;
- lint;
- typecheck;
- tests;
- build.

Segurança:

- `pip-audit`;
- `npm audit`;
- Trivy;
- Gitleaks HEAD/histórico quando aplicável;
- CodeQL/Code Scanning;
- Dependabot/Secret Scanning quando acessíveis.

Smoke:

- `docker compose ps`;
- `/health`;
- `/ready`;
- frontend HTTP;
- Cloudflare hostname no OCI lab;
- `git diff --check`;
- `git status --short`.

No host de baixa capacidade, se Vitest paralelo gerar timeout artificial, executar serialmente com `--maxWorkers=1` e timeout aumentado apenas via CLI; não alterar timeout global do projeto para mascarar limitação de hardware.
