# SGI v2 — Sistema de Gestão de Investimentos

## Ambiente de validação com usuários

O runtime único de testes assistidos é o projeto Compose existente `sig-v2`,
publicado pelo Cloudflare Tunnel. Toda alteração de produto validada com
usuários deve ser incorporada às imagens backend/frontend dessa stack. Não
iniciar `sgi-usertest`; o procedimento atual está em
[`docs/USER_VALIDATION_RUNBOOK.md`](docs/USER_VALIDATION_RUNBOOK.md).

## Simulacoes

A calculadora de aportes esta em `/carteira/ferramentas/rendimentos`; o simulador de Renda Fixa esta em `/carteira/ferramentas/renda-fixa`. No simulador, o tratamento de IR e derivado automaticamente do tipo de produto. Ambos usam premissas informadas pelo usuario e nao modificam a carteira. Formulas, fontes, hipoteses e limites estao em [`docs/TOOLS_CALCULATORS.md`](docs/TOOLS_CALCULATORS.md).

No cadastro de Renda Fixa, o nome do titulo inclui o emissor, o tipo do produto define o tratamento fiscal e a carencia some com liquidez diaria. A taxonomia e as regras estao descritas em [`docs/FIXED_INCOME_TAXONOMY_INVENTORY.md`](docs/FIXED_INCOME_TAXONOMY_INVENTORY.md).

Plataforma para acompanhamento, consolidação, rentabilidade, Proventos, IRPF e evolução patrimonial de carteiras multiclasse, com backend FastAPI e frontend React + TypeScript.

## Branch e governança

- desenvolvimento obrigatório em `stable-15jun`;
- `main` recebe apenas macroblocos certificados via Pull Request;
- cada implementação é dividida em commits pequenos e rastreáveis;
- antes de alterar funcionalidade, revisar a Issue relacionada, contratos canônicos e impacto arquitetural;
- README, ROADMAP, CHANGELOG, Issues e runbooks devem refletir o estado real do projeto.

## Snapshot historico do projeto — 16/10/2026

O SGI v2 está em **pós-GO e hardening arquitetural**. A baseline funcional foi
promovida para `main` pela PR #362 e a certificação persistente para dados reais
foi concluída pela #384 para uma identidade runtime específica. Este status
histórico não certifica o checkout atual nem confirma a identidade atualmente
implantada.

Registro histórico da identidade certificada em 06/10/2026, não aplicável ao
runtime observado nesta baseline:

```text
test_ready=true
user-test-readiness.v1=GO_ASSISTED
go_for_assisted_user_tests=true
ready_for_real_data=true
/health=200
/ready=200
```

### Rebaseline pós-promoção

- PR #425 sincronizou `main` para `stable-15jun`. Desde então, `stable-15jun`
  avançou e está 7 commits à frente, 0 atrás de `main`; o checkout está no SHA
  `b37661921e3a8455f45c8b676b28955d6ad3d0ea` e coincide com `origin/stable-15jun`.
- O inventário GitHub de 16/10/2026 encontrou 23 Issues abertas e nenhuma PR
  aberta. O quadro por prioridade está em `docs/ISSUE_GOVERNANCE.md`.
- #408: a sanitização dos logs está em `stable-15jun` pela PR #413 e
  as regressões chegaram pela #419; a CI da #419 passou. A Issue segue aberta
  até uma análise CodeQL posterior à correção confirmar os findings.
- #83: download, reautenticação de restore, auditoria, status persistido de
  operações e retenção já têm implementação no código estável. Falta comprovar
  o ciclo integrado de backup e restore isolado antes de tratar a interface
  como disaster recovery certificado.

- #363 fechado apos recuperacao dos gates tecnicos locais.
- #354 permanece fechada.
- #352 foi validada manualmente e fechada: `Tipo de ativo` virou caixa seletora
  no modal de lancamento, e a transacao foi adicionada com sucesso.
- #158, #269 e #227 estão fechadas; a PR #362 foi mergeada em `main`;
- OCI/#284 saiu do caminho crítico atual e permanece backlog futuro de
  infraestrutura/cloud;
- a #384 foi concluída com evento `PROMOTE` append-only, validação DB-first e
  persistência comprovada após restart; qualquer nova identidade de runtime
  exige novo ciclo de certificação;
- #370 avancou a fronteira de eventos corporativos materiais: a varredura de
  22/09/2026 registrou zero eventos materiais em `UNRECONCILED`; AMOB3 esta
  formalizada como `MATCHED`/`CONFLICT`, e KLBN11 permanece em `CONFLICT`
  revisavel ate haver evidencia documental de liquidacao fracionaria para
  eventual `MATCHED`.
- a Epic #344 foi concluída: #345–#350 estão fechadas e os blocos de Doctor,
  Agent Skills, Certification Proof, runtime determinístico, Access Context e
  Reliable Async foram promovidos para `main`;
- #384 possui persistência append-only, leitura DB-first, relatório, contrato,
  executor transacional e CLI guardada; a promoção operacional real foi
  executada para o dataset/SHA registrados e `/ready` consome essa autoridade.

`GO_ASSISTED` continua descrevendo apenas testes acompanhados. A autorização
para dados reais depende exclusivamente do evento persistido da #384 e da
correspondência exata da identidade; a CLI assistida não altera `/ready`.

### Runtime local observado — 16/10/2026

- backend, PostgreSQL e Redis estão saudáveis; `/health` retornou `ok`;
- `/ready` retornou `503` com `runtime_identity_error` e
  `ready_for_real_data=false`;
- o container declara `APP_BRANCH=stable-15jun` e `ENVIRONMENT=testing`, mas sua
  `APP_COMMIT_SHA` diverge do HEAD e `REAL_DATASET_REFERENCE` está vazia;
- o working tree contém alterações locais de código e documentação, além de
  artefatos candidatos não rastreados; a revisão inicial identificou trabalho
  ainda não consolidado de eventos corporativos;
- a consulta read-only atual de `user_test_readiness` não concluiu nem produziu
  relatório antes do timeout; não há readiness assistida atual confirmada.
  Consulte `docs/DEVELOPMENT_BASELINE_2026-10-16.md`.

O status do checkout e do runtime, com o mapa de desenvolvimento, está em
`docs/DEVELOPMENT_BASELINE_2026-10-16.md`. A certificação de 06/10 é histórica;
o runtime atual não está certificado para dados reais.

### Candidato implantado — 17/10/2026

O candidato local foi implantado em `production`, com Alembic em
`20261016_corp_ev_effective_date`. A identidade exata de cada build fica no
proof gerado para o runtime corrente em `artifacts/certification-proof/`.
Backend, frontend,
PostgreSQL e Redis estão ativos; readiness assistida retornou `GO_ASSISTED`,
sem blockers/warnings e sem escritas. O `/ready` permanece 503 porque o evento
persistido anterior certifica outra identidade. Backup v3 pós-migration, restore
isolado e dry-run #384 passaram sem promover. Qualquer novo SHA exige backup,
restore e dry-run próprios; os relatórios e o mapa estão em `artifacts/` e
`docs/DEVELOPMENT_BASELINE_2026-10-16.md`.

A cadeia histórica de promoção foi concluída. O próximo ciclo vigente está em
`ROADMAP.md` e `docs/DEVELOPMENT_BASELINE_2026-10-16.md`:

```text
consolidar o candidato local e as migrations
        -> gates de código, Doctor e CodeQL #408
        -> backup v3 e restore isolado #83
        -> atualizar e validar imagem / readiness assistida
        -> dry-run e certificação guardada #384
        -> GOV-07/#293 e uma entrega de produto

#384 foi concluída para a identidade registrada; promoções futuras continuam vinculadas à identidade exata.
#284 permanece backlog futuro e não bloqueia desenvolvimento local.
```

## Agent Skills versionadas

Instruções operacionais para agentes vivem em `.agents/skills` e devem ser
atualizadas no mesmo bloco que alterar um contrato correspondente:

- `sgi-development` — branch, governança, Architecture Doctor e testes;
- `sgi-financial-data` — ledger, projeções e writes financeiros;
- `sgi-market-data` — providers, provenance, seeds e eventos corporativos;
- `sgi-certification` — identidade, `/ready`, promoção e revogação.

As skills orientam a leitura dos contratos vivos; não substituem Issues,
runbooks, testes ou autorização explícita para operações destrutivas/escritas.

## Ambiente de desenvolvimento e OCI

### Local

Windows + PowerShell + Docker é o ambiente oficial de desenvolvimento, correção, migrations de teste, suítes pesadas, certificação financeira e geração do SHA candidato.

### OCI

OCI não faz parte do caminho atual de desenvolvimento, testes ou homologação.
#284 preserva o trabalho de infraestrutura/cloud como backlog futuro.

Quando esse backlog for retomado, não desenvolver nem manter hotfix permanente
na VM.

## Arquitetura financeira canônica

```text
bootstrap / sincronizadores explicitamente autorizados
        ↓
assets + asset_prices + rate_history + fx_rates
asset_dividends + corporate_events
        ↓
transactions
        ↓
projeções canônicas de posição, custo e resultado
        ↓
valuation dedicado por classe
        ↓
PortfolioSnapshot + PortfolioClassSnapshot
        ↓
summary.v2 + rentabilidade.v2 + leitores históricos
        ↓
Resumo / Patrimônio / Rentabilidade / Proventos / IRPF
```

Princípios obrigatórios:

- runtime financeiro DB-first;
- provider não participa de GET/cálculo financeiro;
- ausência não vira zero, câmbio fixo ou preço inventado;
- dados externos são persistidos antes de entrar em contratos financeiros;
- `transactions` é a fonte canônica do lifecycle, inclusive Renda Fixa e Tesouro;
- Proventos pertencem ao ativo em `asset_dividends`;
- o seed isolado de Proventos publica o contrato `pre-prod-dividends-seed.v2`; direitos de carteira são calculados sob demanda a partir das posições históricas, sem materialização por carteira;
- eventos corporativos pertencem ao ativo em `corporate_events`;
- rebuilds e seeds são operações explícitas e auditáveis.

## Estado funcional resumido

| Domínio | Estado em 11/10/2026 |
|---|---|
| Autenticação/Core | funcional em validação assistida |
| Carteiras/Transações | canônico e certificado sinteticamente |
| CSV | certificado |
| Patrimônio/Resumo | reconciliado em carteira assistida |
| Snapshots | rebuild/replay certificados |
| Rentabilidade | TWR dedicado de Tesouro e Renda Fixa disponível; lacunas permanecem explícitas |
| Tesouro | valuation DB-first, snapshots dedicados e eventos monetários consumidos uma vez |
| Renda Fixa | lifecycle transaction-derived, valuation e TWR dedicados |
| Proventos | `pre-prod-dividends-seed.v2` asset-based; direitos calculados sob demanda; prova portfolio-scoped idempotente |
| Eventos corporativos | sem `UNRECONCILED` material; KLBN11 em `CONFLICT` revisável |
| IRPF | funcional para classes suportadas |
| Metas | superfície básica funcional; desenho definitivo permanece #246 |
| Detalhe de ativo | parcialmente implementado (#58/#351) |
| Analysis Engine | planejado (#360) |
| IA | planejada após #360/#246 (#361) |

## Pendências financeiras pós-GO

- #352 — seleção de classe; fechada após validação manual do seletor `Tipo de ativo`;
- #354 — regra de senha; fechado após alinhamento frontend/backend no SHA `f93f5a2eff0ef2c1f797209577af8d2934d8c9b0`;
- #370 permanece fail-closed para KLBN11 até evidência documental suficiente;
- #384 foi concluída e mantém a liberação para dados reais explícita,
  persistente e separada da promoção para `main`.

#149 permanece aberta para evidência de posição de custódia por carteira na
manhã do pagamento e base tributável/IRRF por lote. A regra oficial de
elegibilidade está documentada; certificação de runtime é gate separado de
promoção para dados reais, não requisito de desenvolvimento. Os contratos de
TWR dedicado já estão cobertos por oracles; lacunas de PU, benchmark ou
calendário continuam fail-closed e não são apresentadas como retorno oficial.

## Evolução pós-GO

#351, #90, #58, #355–#361 e #97 permanecem backlog de evolução conforme classificação nas Issues.

## Comandos básicos

```bash
cp .env.example .env
docker compose up -d --build
```

Backend:

```bash
cd backend
python -m ruff check app tests
python -m compileall -q app tests
pytest -q
```

Frontend:

```bash
cd frontend
npm run typecheck
npm run lint
npm test -- --run
npm run build
```

Gate assistido:

```bash
docker compose run --rm backend python -m app.cli.user_test_readiness
```

## Documentação canônica

- `ROADMAP.md`;
- `CHANGELOG.md`;
- `docs/DEVELOPMENT_CONTINUITY.md`;
- `docs/architecture.md`;
- `docs/USER_TEST_READINESS_GATE.md`;
- `docs/USER_VALIDATION_RUNBOOK.md`;
- `docs/BOOTSTRAP_DATA_FLOW.md`;
- `docs/REAL_DATA_CERTIFICATION_RUNBOOK.md`;
- `docs/deployment/oci-execution-index.md` (referência futura OCI);
- Issues #408, #83, #293, #149, #370 e #284 (estados atuais e backlog).

## Status atual — 17/10/2026

O runtime consultado nesta data esta no SHA `5c4ad390`, saudavel e com `/ready=200` para a identidade certificada registrada. A Issue #83 foi concluida no GitHub apos ensaio administrativo integrado em dois bancos descartaveis; procedimento em `docs/ADMIN_BACKUP_RESTORE_REHEARSAL.md`. #408 continua aguardando confirmacao CodeQL posterior as correcoes e GOV-07/#293 segue como proximo bloco de governanca. Este status atualiza fotografias anteriores deste README, preservadas como historico.

### Atualizacao de governanca — 17/10/2026

O inventario GitHub ao vivo encontrou 22 Issues abertas e nenhuma PR aberta.
GOV-07 foi correlacionada no snapshot local sem encontrar Issue claramente
duplicada ou sem destino. #353 ja tem scroll restoration global e testes
unitarios; faltam validacoes desktop/mobile, sem bloquear a jornada critica.
#293 segue aberta ate reconciliar/publicar a documentacao porque a ponta remota
`stable-15jun` nao foi obtida (consulta Git indisponivel). #408 segue aberta ate
reconciliar a evidencia CodeQL divergente. Ver `docs/ISSUE_GOVERNANCE.md`.
