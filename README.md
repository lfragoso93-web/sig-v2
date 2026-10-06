# SGI v2 — Sistema de Gestão de Investimentos

Plataforma para acompanhamento, consolidação, rentabilidade, Proventos, IRPF e evolução patrimonial de carteiras multiclasse, com backend FastAPI e frontend React + TypeScript.

## Branch e governança

- desenvolvimento obrigatório em `stable-15jun`;
- `main` recebe apenas macroblocos certificados via Pull Request;
- cada implementação é dividida em commits pequenos e rastreáveis;
- antes de alterar funcionalidade, revisar a Issue relacionada, contratos canônicos e impacto arquitetural;
- README, ROADMAP, CHANGELOG, Issues e runbooks devem refletir o estado real do projeto.

## Status atual — 06/10/2026

O SGI v2 está em **pós-GO e hardening arquitetural**. A baseline funcional foi
promovida para `main` pela PR #362 e a certificação persistente para dados reais
foi concluída pela #384 para a identidade runtime atualmente implantada.

Estado operacional registrado:

```text
test_ready=true
user-test-readiness.v1=GO_ASSISTED
go_for_assisted_user_tests=true
ready_for_real_data=true
/health=200
/ready=200
```

### Rebaseline pós-promoção

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
- #345 foi concluída e promovida para `main` pela PR #385; a sequência da Epic
  #344 continua em #346 e #347;
- #384 possui persistência append-only, leitura DB-first, relatório, contrato,
  executor transacional e CLI guardada; a promoção operacional real foi
  executada para o dataset/SHA registrados e `/ready` consome essa autoridade.

`GO_ASSISTED` continua descrevendo apenas testes acompanhados. A abertura atual
para dados reais vem exclusivamente do evento persistido da #384; a CLI
assistida não altera `/ready` manualmente.

A cadeia histórica de promoção foi concluída. O mapa vigente é:

```text
governança pós-#362
        -> baseline local do HEAD
        -> #345 Architecture Doctor (concluída)
        -> #346 Agent Skills
        -> #347 Certification Proof
        -> #365 antes de qualquer migration ampla de #364

#384 foi concluída; promoções futuras continuam vinculadas à identidade exata.
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

| Domínio | Estado em 10/09/2026 |
|---|---|
| Autenticação/Core | funcional em validação assistida |
| Carteiras/Transações | canônico e certificado sinteticamente |
| CSV | certificado |
| Patrimônio/Resumo | reconciliado em carteira assistida |
| Snapshots | rebuild/replay certificados |
| Rentabilidade | funcional; TWR RF permanece #149 |
| Tesouro | valuation DB-first e snapshots dedicados |
| Renda Fixa | lifecycle transaction-derived e valuation dedicado |
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

#149 não bloqueia automaticamente o primeiro GO se TWR de RF continuar explicitamente indisponível e nenhum fallback for apresentado como TWR.

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
- Issues #344, #345, #365, #364, #370, #384 e #284 (backlog futuro).
