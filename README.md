# SGI v2 — Sistema de Gestão de Investimentos

Plataforma pessoal para acompanhamento, consolidação e análise de investimentos, com backend FastAPI e frontend React + TypeScript.

A branch de desenvolvimento é `stable-15jun`. A promoção para `main` ocorre exclusivamente por Pull Request após validação integral e sincronização da documentação viva.

## Status atual — 07/08/2026

O SGI v2 está em **estabilização arquitetural final da base antes da próxima grande fase funcional**. O gate operacional da Issue #227 continua impedindo cargas reais não autorizadas. A convergência Alembic ↔ MetaData da Issue #241 está concluída para todos os domínios do escopo, com uma única exceção arquitetural consciente: `goals`.

### Qualidade validada

- Build Docker: aprovado no HEAD `17beeb9e6ae70f51d523e273bebda368872f81de`.
- `compileall`: aprovado.
- Suíte estrutural final: 15 testes aprovados.
- Import integral de `app.main`: aprovado.
- Consumers legados removidos e gates de regressão ativos.
- Alembic/ORM convergidos fora de `goals`.

### Entregas consolidadas

- Arquitetura DB-first e contratos `summary.v2` e `rentabilidade.v2`.
- Valuation canônico por classe, snapshots patrimoniais e reconciliação financeira.
- Histórico B3/COTAHIST, Tesouro oficial, benchmarks e câmbio persistidos.
- Leitura pública USD/BRL servida exclusivamente por `fx_rates`, com MetaData/ORM alinhados ao schema migrado.
- Proventos globais em `asset_dividends`, com direitos de carteira calculados sob demanda.
- Motor canônico de eventos corporativos e projeção histórica de posição, custo e resultado realizado.
- IRPF anual canônico com Day Trade, Swing Trade, isenção mensal, prejuízos, IRRF e DARF mínima.
- Contratos públicos versionados de apuração anual, Bens e Direitos, Rendimentos e Ganhos de Capital.
- IRPF frontend integralmente canônico, sem persistência ou consumo de `IRPFReport` legado.
- Exportações PDF e CSV compostas diretamente pelos contratos canônicos.
- Transactions alinhado ao contrato físico migrado: tipos financeiros, nulabilidade, índices, notas e timestamps.
- Snapshots, ativos, Proventos, eventos corporativos, Renda Fixa, configurações, usuários e portfólios alinhados à cadeia Alembic.
- `app_config`, `IRPFReport`, `irpf_records`, `irpf_losses` e `goal_allocations` tratados por decisões explícitas e contrações defensivas quando aplicável.
- Alembic endurecido com gates contra autogenerate monolítico e remoções acidentais.
- PRs estruturais #237 e #240 já promovidas e mergeadas na `main`.

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
Resumo / Patrimônio / Rentabilidade / Proventos / IRPF
```

Metas não participa, neste momento, do conjunto de contratos canônicos estabilizados. O módulo `goals` será redesenhado em conjunto com Análise de Carteira nas Issues #246 e #57.

Princípios: DB-first, fonte oficial primeiro, idempotência, ausência não convertida em zero, contratos financeiros únicos e nenhuma chamada a provedor durante cálculos financeiros.

## Estado operacional

- Seeds de benchmarks e câmbio: executados e reconciliados.
- Seed canônico de Proventos usa o contrato `pre-prod-dividends-seed.v2`: implementação concluída; duas execuções reais controladas ainda pendentes.
- O contrato v2 persiste somente eventos globais em `asset_dividends`; direitos de carteira são calculados sob demanda.
- Contração física das tabelas legadas de Proventos: preparada, mas não executada.
- Importação CSV real, posições e snapshots: suspensos até o encerramento da #227.
- O boot não executa sincronização de mercado por padrão.
- Rebuilds e seeds externos devem permanecer explicitamente opt-in.
- `alembic upgrade head`, reexecução idempotente e convergência dos domínios estabilizados foram aprovados.
- O diff remanescente do `alembic check` está limitado a `goals` e é exceção deliberada rastreada pela #246; nenhuma migration deve ser criada para silenciá-lo antes do redesenho conjunto com #57.
- O endpoint `/usd-brl` lê a última cotação persistida de `fx_rates` e retorna indisponibilidade explícita quando não existe cobertura.

## Próximas prioridades

1. Encerrar formalmente a #241 com a exceção `goals` documentada e rastreada pela #246/#57.
2. Revisar arquitetura, serviços, routers, endpoints e legado remanescente após a estabilização Alembic/ORM.
3. Consolidar consumidores restantes do motor de eventos corporativos (#129), caso ainda existam após a auditoria global.
4. Evoluir aliases, cobertura e adapters por capacidade (#130 e #127).
5. Implementar IBOV persistido e TWR dedicado (#150 e #149).
6. Retomar seeds, importação e rebuild somente após os gates arquiteturais (#158, #216, #226 e #227).
7. Somente depois iniciar o macroprojeto conjunto de Metas + Análise de Carteira (#246 + #57).

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
- `docs/ALEMBIC_METADATA_DRIFT_INVENTORY_2026-08.md` — matriz de deriva Alembic/ORM e exceção `goals`.
- `docs/FX_AND_GOAL_CONSUMER_INVENTORY_2026-08.md` — inventário de consumidores de câmbio e metas.
- `docs/PRE_PROD_REBUILD_RUNBOOK.md` — gates operacionais de pré-produção.
