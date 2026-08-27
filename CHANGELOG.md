# Changelog — SGI v2

Todas as mudanças relevantes do projeto são documentadas aqui.
Formato baseado em Keep a Changelog.

## [Unreleased] — branch `stable-15jun`

### Alterado — CERT-01B e hardening do runtime frontend (27/08/2026)

- CERT-01A foi aprovado no OCI lab sobre `d7c03078c9b31cfd004e88e321557ddc0f0658fe`: backend `1623 passed, 35 skipped`, `pip-audit` sem vulnerabilidades conhecidas, frontend completo aprovado, contratos de seed/bootstrap aprovados sem seed real, smoke HTTP descartável aprovado e `ready_for_real_data=false` preservado.
- CERT-01B foi iniciado com `scripts/oci_certification_security.sh`, cobrindo Gitleaks full history, Trivy filesystem, Hadolint e Trivy das imagens runtime backend/frontend.
- O primeiro CERT-01B encontrou `AVD-DS-0002` HIGH no runtime frontend por ausência de `USER` não-root.
- O Dockerfile frontend canônico passa a executar Nginx como usuário `nginx`, mantendo porta interna 80 somente com `CAP_NET_BIND_SERVICE` mínima.
- `docker-compose.prod.yml` converge para o Dockerfile frontend canônico; `frontend/Dockerfile.prod` legado foi removido para eliminar deriva de segurança/build.
- CERT-01B permanece pendente até reexecução integral e reconciliação dos inventários externos de CodeQL/Code Scanning, Dependabot Security Alerts e Secret Scanning.

### Alterado — rebaseline para certificação OCI e testes integrados (27/08/2026)

- O projeto entrou formalmente em fase de certificação operacional: novas funcionalidades ficam subordinadas à conclusão dos gates de teste e readiness.
- Baseline de retomada registrado: `stable-15jun` em `a889edb6bbbb78feb7787c21b3439a0b835b73c6` e `main` em `3eeca232a8627f4562544739112d1dde82b879fb`.
- PRs #290, #291 e #292 passam a compor o baseline de laboratório OCI: build frontend, Cloudflare HTTP/2 200, smoke OCI e validação repetível dos contratos de bootstrap sem seeds reais.
- Evidências de contrato registradas: FX/Macro/Tesouro `81 passed, 1 skipped`; B3/Asset Bootstrap/System Bootstrap `70 passed`; Proventos `93 passed, 8 skipped`.
- O smoke HTTP descartável passou a validar também o gate de SuperAdmin em `/api/v1/admin/bootstrap/status`, exigindo `403` para usuário comum.
- `test_ready=true` permanece válido para dados fictícios/descartáveis; `ready_for_real_data=false` permanece obrigatório.
- Ordem canônica atual: certificar lab e persistência → revalidar #227/#226/#216/#158 → executar operações reais somente quando autorizadas → reconciliar → GO/NO-GO.
- A PR Dependabot #289, TypeScript 7, permanece bloqueada por incompatibilidade com `typescript-eslint 8.67.0` e não deve ser mergeada no estado atual.
- README, ROADMAP e `docs/DEVELOPMENT_CONTINUITY.md` foram sincronizados com este rebaseline.

### Alterado — baseline pós-segurança e gate para teste real (18/08/2026)

- A sanitização arquitetural da #247 foi consolidada como concluída e promovida pela PR #281.
- O bloco final de segurança da #269 foi promovido pela PR #282, cobrindo confinamento de paths de backup, sanitização residual de logs e publicação SARIF do Trivy da imagem backend.
- `test_ready=true` permanece preservado; `ready_for_real_data=false` continua obrigatório.
- A Issue #227 passa a refletir o novo foco: revalidar #226/#216/#158 e executar o TESTE REAL controlado somente quando os gates formais permitirem.
- README, ROADMAP e `docs/DEVELOPMENT_CONTINUITY.md` foram sincronizados para remover o estado obsoleto que ainda tratava a #247 como trabalho corrente.
- O `Security deep scan` continua sendo verificação periódica semanal/manual; a documentação não presume execução de scanners sem evidência explícita.

### Alterado — composição explícita do full market rebuild (15/08/2026)

- `full_market_rebuild_canonical_service.py` deixou de alterar temporariamente funções internas do orquestrador base por monkey-patching.
- `full_market_rebuild_service.py` passou a receber explicitamente as operações de Tesouro, snapshots e leitura do resumo, preservando defaults e ordem das etapas.
- A CLI canônica permanece em `python -m app.cli.full_market_rebuild`; nenhum rebuild, provider ou dado real foi executado durante a refatoração.
- Adicionado gate estrutural contra a reintrodução de mutação global entre as duas camadas.

### Removido — exemplo de ambiente paralelo e desatualizado (15/08/2026)

- Removido `backend/.env.example`, que duplicava o contrato canônico da raiz e ainda documentava `DEBUG_RATE_LIMIT`, `ADMIN_SECRET`, router de debug e fallback via yfinance já removidos.
- `.env.example` da raiz permanece como fonte única para aplicação, Docker Compose, frontend, bootstrap e operações controladas.
- Adicionado gate estrutural exigindo a presença do exemplo canônico e a ausência do duplicado no backend.

### Removido — hooks residuais sem consumidores (15/08/2026)

- Removidos `useAssets`, `useFxRate`/`useUsdBrl` e `assetService`, sem consumidores após a limpeza das páginas paralelas.
- Leituras financeiras ativas continuam pelos readers/hooks específicos e DB-first.
