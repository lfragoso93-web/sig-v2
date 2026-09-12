# SGI v2 — Sistema de Gestão de Investimentos

Plataforma para acompanhamento, consolidação, rentabilidade, Proventos, IRPF e evolução patrimonial de carteiras multiclasse, com backend FastAPI e frontend React + TypeScript.

## Branch e governança

- desenvolvimento obrigatório em `stable-15jun`;
- `main` recebe apenas macroblocos certificados via Pull Request;
- cada implementação é dividida em commits pequenos e rastreáveis;
- antes de alterar funcionalidade, revisar a Issue relacionada, contratos canônicos e impacto arquitetural;
- README, ROADMAP, CHANGELOG, Issues e runbooks devem refletir o estado real do projeto.

## Status atual — 10/09/2026

O SGI v2 está em **certificação final assistida**, não em construção do núcleo.

Estado operacional registrado:

```text
test_ready=true
user-test-readiness.v1=GO_ASSISTED
go_for_assisted_user_tests=true
ready_for_real_data=false
/health=200
/ready=503
```

`GO_ASSISTED` permite testes acompanhados com massa sintética/controlada. Não autoriza abertura ampla com dados reais e não altera `/ready` manualmente.

A cadeia obrigatória para promoção é:

```text
#303 PORTFOLIO-TEST-READY
        ↓
#226 Proventos
        ↓
#216 gate agregado
        ↓
#158 promotion reconciliation
        ↓
OCI homologa o SHA exato
        ↓
#227 GO / NO-GO
        ↓
somente após GO: avaliar ready_for_real_data=true
```

## Ambiente de desenvolvimento e OCI

### Local

Windows + PowerShell + Docker é o ambiente oficial de desenvolvimento, correção, migrations de teste, suítes pesadas, certificação financeira e geração do SHA candidato.

### OCI

OCI é ambiente de homologação do SHA já certificado localmente: deploy exato, migrations aprovadas, smoke, restart, persistência, recursos, rede, Cloudflare Tunnel e checks de segurança/resiliência.

Não desenvolver nem manter hotfix permanente na VM. Falha encontrada em OCI volta ao ambiente local, gera novo SHA e nova homologação.

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
| Eventos corporativos | reconciliação material ainda pendente para casos complexos |
| IRPF | funcional para classes suportadas |
| Metas | superfície básica funcional; desenho definitivo permanece #246 |
| Detalhe de ativo | parcialmente implementado (#58/#351) |
| Analysis Engine | planejado (#360) |
| IA | planejada após #360/#246 (#361) |

## Itens que podem afetar o primeiro GO

- #352 — seleção de classe; P1 se ainda impedir/errar lançamento;
- #354 — regra de senha; P1 se frontend/backend ainda divergirem;
- eventos corporativos materiais ao dataset de promoção;
- fechamento #303 → #226 → #216 → #158 → #227.

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
- `docs/deployment/oci-execution-index.md`;
- Issues #303, #226, #216, #158, #227, #284 e #293.
