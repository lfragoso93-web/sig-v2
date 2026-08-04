# SGI v2 — Sistema de Gestão de Investimentos

Plataforma pessoal para acompanhamento, consolidação e análise de investimentos, com backend FastAPI e frontend React + TypeScript.

A branch de desenvolvimento é `stable-15jun`. A promoção para `main` ocorre exclusivamente por Pull Request após validação integral e sincronização da documentação viva.

## Status atual — 04/08/2026

O SGI v2 está em **consolidação arquitetural antes da primeira carga real de carteiras e usuários**. O gate vigente é a Issue #227: seeds, sincronizações externas, importação real e rebuild operacional permanecem opt-in e suspensos até a certificação do núcleo financeiro.

### Qualidade validada

- Backend: `1265 passed`, `22 skipped` na suíte completa mais recente.
- Ruff e `compileall`: aprovados nos gates do módulo IRPF.
- Frontend: 26 arquivos de teste e 93 testes aprovados.
- Typecheck, ESLint e build de produção: aprovados.

### Entregas consolidadas

- Arquitetura DB-first e contratos `summary.v2` e `rentabilidade.v2`.
- Valuation canônico por classe, snapshots patrimoniais e reconciliação financeira.
- Histórico B3/COTAHIST, Tesouro oficial, benchmarks e câmbio persistidos.
- Proventos globais em `asset_dividends`, com direitos de carteira calculados sob demanda.
- Motor canônico de eventos corporativos e projeção histórica de posição, custo e resultado realizado.
- IRPF anual canônico com Day Trade, Swing Trade, isenção mensal, prejuízos, IRRF e DARF mínima.
- Contratos públicos versionados de apuração anual, Bens e Direitos, Rendimentos e Ganhos de Capital.
- IRPF frontend integralmente canônico, sem carregamento de `IRPFReportOut`.
- Exportações PDF e CSV compostas diretamente por `IrpfCanonicalExport`.
- Endpoint completo legado do IRPF preservado apenas para compatibilidade externa, sem uso pela interface ou exportações.
- Backup/restore e defaults ORM modernizados para UTC sem warnings de `datetime.utcnow()`.
- IRPF e Metas sob o contexto canônico da carteira:
  - `/carteira/irpf`;
  - `/carteira/metas`.
- Rotas antigas `/irpf` e `/metas` mantidas temporariamente apenas como redirects.

## Arquitetura resumida

```text
Importação CSV / lançamentos manuais
        ↓
transactions + fixed_income_investments + corporate_events
        ↓
projeções canônicas de posição, custo e realizações
        ↓
catálogo, preços, taxas e proventos persistidos
        ↓
valuation dedicado por classe
        ↓
PortfolioSnapshot + PortfolioClassSnapshot
        ↓
summary.v2 / rentabilidade.v2 / leitores históricos
        ↓
Resumo / Patrimônio / Rentabilidade / Proventos / Metas / IRPF
```

Princípios: DB-first, fonte oficial primeiro, idempotência, ausência não convertida em zero, contratos financeiros únicos e nenhuma chamada a provedor durante cálculos financeiros.

## Estado operacional

- Seeds de benchmarks e câmbio: executados e reconciliados.
- Seed canônico de Proventos usa o contrato `pre-prod-dividends-seed.v2`: implementação concluída; duas execuções reais controladas ainda pendentes.
- O contrato v2 persiste somente eventos globais em `asset_dividends`; direitos de carteira são calculados sob demanda.
- Contração física das tabelas legadas de Proventos: preparada, mas não executada.
- Importação CSV real, posições e snapshots: suspensos até o encerramento da #227.
- O boot não executa sincronização de mercado por padrão.
- Rebuilds e seeds externos devem permanecer explicitamente opt-in.

## Próximas prioridades

1. Promover o módulo IRPF canônico e o macrobloco estrutural para a `main` por PR.
2. Concluir consumidores remanescentes e remover a fachada legada de Rentabilidade (#151).
3. Consolidar eventos corporativos e adapters por capacidade (#129, #130 e #127).
4. Implementar IBOV persistido e TWR dedicado (#150 e #149).
5. Retomar seeds, importação e rebuild somente após os gates arquiteturais (#158, #216, #226 e #227).
6. Validar o IRPF em carteira real com operações representativas quando houver dados homologados.

## Comandos principais

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

## Documentação viva

- `ROADMAP.md` — prioridades e andamento modular.
- `CHANGELOG.md` — mudanças relevantes.
- `docs/architecture.md` — arquitetura DB-first e fronteiras dos módulos.
- `docs/DEVELOPMENT_CONTINUITY.md` — checkpoint obrigatório para retomada.
- `docs/RENTABILIDADE_IRPF_CANONICAL_MIGRATION_PLAN.md` — plano do núcleo financeiro.
- `docs/IRPF_CANONICAL_FRONTEND_INTEGRATION.md` — contratos e fronteiras atuais do frontend e das exportações.
- `docs/portfolio-route-hierarchy.md` — hierarquia das rotas vinculadas à carteira.
- `docs/DIVIDENDS_CANONICAL_ARCHITECTURE.md` — arquitetura canônica de Proventos.
- `docs/PRE_PROD_REBUILD_RUNBOOK.md` — gates operacionais de pré-produção.
