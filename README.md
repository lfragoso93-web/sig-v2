# SGI v2 — Sistema de Gestão de Investimentos

Plataforma pessoal para acompanhamento, consolidação e análise de investimentos, com backend FastAPI e frontend React + TypeScript.

A branch de desenvolvimento é `stable-15jun`. A promoção para `main` ocorre exclusivamente por Pull Request após validação integral e sincronização da documentação viva.

## Status atual — 07/08/2026

O SGI v2 está em **estabilização arquitetural e reorganização de governança antes da próxima fase funcional**.

A Issue #227 é o gate-mãe que bloqueia dados reais até a certificação estrutural. A Issue #247 executa a etapa atual: primeiro reconciliar documentação, Issues e PRs; depois auditar legado, serviços, routers e endpoints.

A convergência Alembic ↔ MetaData da Issue #241 foi concluída para todos os domínios estabilizados. O único diff deliberadamente preservado é `goals`, que não deve receber migration antes do redesenho conjunto de Metas e Análise de Carteira (#246 + #57).

### Qualidade validada

Baseline estrutural registrada no HEAD `17beeb9e6ae70f51d523e273bebda368872f81de`:

- Build Docker aprovado.
- `compileall` aprovado.
- Suíte estrutural final: 15 testes aprovados.
- Import integral de `app.main` aprovado.
- Consumers legados removidos e gates de regressão ativos.
- Alembic/ORM convergidos fora de `goals`.

Os commits documentais posteriores não alteraram runtime, schema ou contratos financeiros.

### Entregas consolidadas

- Arquitetura DB-first e contratos `summary.v2` e `rentabilidade.v2`.
- Valuation canônico por classe, snapshots patrimoniais e reconciliação financeira.
- Histórico B3/COTAHIST, Tesouro oficial, benchmarks e câmbio persistidos.
- Leitura pública USD/BRL exclusivamente por `fx_rates`, alinhado ao MetaData/Alembic.
- Proventos globais em `asset_dividends`, com direitos de carteira calculados sob demanda.
- Motor canônico de eventos corporativos e projeção histórica compartilhada de posição, custo e resultado realizado.
- IRPF anual canônico, frontend e exportações sem persistência de `IRPFReport` legado.
- Transactions alinhado ao contrato físico migrado.
- Snapshots, ativos, Proventos, eventos corporativos, Renda Fixa, configurações, usuários e portfólios alinhados à cadeia Alembic.
- `app_config`, `IRPFReport`, `irpf_records`, `irpf_losses` e `goal_allocations` tratados por decisões explícitas e contrações defensivas quando aplicável.
- Alembic endurecido com gates contra autogenerate monolítico e remoções acidentais.

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

Metas e Análise de Carteira estão fora do conjunto de contratos funcionais estabilizados neste momento. O redesenho será tratado como um único macroprojeto pelas Issues #246 e #57 somente depois da estabilização definitiva da base.

Princípios: DB-first, fonte oficial primeiro, idempotência, ausência não convertida em zero, contratos financeiros únicos e nenhuma chamada a provedor durante cálculos financeiros.

## Ordem canônica de trabalho

### Agora — governança e auditoria estrutural

1. Reconciliar documentação viva e todas as Issues abertas (#247).
2. Classificar Issues em trabalho atual, bloqueadas/dependentes e backlog.
3. Revisar PRs Dependabot separadamente do roadmap funcional.
4. Auditar routers, serviços, endpoints, aliases, integrações e legado remanescente (#247).
5. Confirmar o estado real de consumidores restantes de eventos corporativos (#129) e itens de provedores relacionados (#130/#127).

### Depois — performance e benchmarks

6. Materializar histórico persistido do IBOV (#150).
7. Implementar TWR dedicado de Tesouro Direto e Renda Fixa (#149).

### Bloqueado até certificação estrutural

8. Executar as duas rodadas reais controladas de Proventos (#226).
9. Fechar o gate agregado de seeds (#216).
10. Retomar rebuild, CSV, posições, snapshots e reconciliação (#158).

### Próxima grande fase funcional

11. Redesenhar Metas + Análise de Carteira como um único macroprojeto (#246 + #57).

Backlog de produto não bloqueador inclui #58, #83, #90, #97 e evoluções amplas de #127/#130 que não sejam necessárias para resolver achados concretos da auditoria atual.

## Estado operacional

- Seeds de benchmarks e câmbio: executados e reconciliados.
- Seed canônico de Proventos: implementação concluída no contrato `pre-prod-dividends-seed.v2`; duas execuções reais controladas permanecem bloqueadas pelo gate arquitetural.
- Contração física das tabelas legadas de Proventos: preparada, não executada.
- Importação CSV real, posições e snapshots: suspensos pela #227.
- O boot não executa sincronização de mercado por padrão.
- Rebuilds e seeds externos permanecem explicitamente opt-in.
- O diff remanescente do `alembic check` está limitado a `goals` e é exceção deliberada rastreada pela #246; nenhuma migration deve ser criada para silenciá-lo antes do redesenho conjunto com #57.

## PRs de dependências

PRs Dependabot abertas são tratadas como fila técnica separada da ordem funcional. Devem ser avaliadas individualmente por risco, compatibilidade e CI antes de qualquer merge.

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

- `ROADMAP.md` — ordem canônica, estado modular e gates.
- `CHANGELOG.md` — mudanças relevantes.
- `docs/architecture.md` — arquitetura DB-first e fronteiras dos módulos.
- `docs/DEVELOPMENT_CONTINUITY.md` — checkpoint obrigatório para retomada.
- `docs/RENTABILIDADE_IRPF_CANONICAL_MIGRATION_PLAN.md` — histórico do núcleo financeiro.
- `docs/IRPF_CANONICAL_FRONTEND_INTEGRATION.md` — contratos do frontend/exportações de IRPF.
- `docs/portfolio-route-hierarchy.md` — hierarquia das rotas vinculadas à carteira.
- `docs/DIVIDENDS_CANONICAL_ARCHITECTURE.md` — arquitetura canônica de Proventos.
- `docs/ALEMBIC_METADATA_DRIFT_INVENTORY_2026-08.md` — inventário final da convergência e exceção `goals`.
- `docs/FX_AND_GOAL_CONSUMER_INVENTORY_2026-08.md` — inventário histórico de câmbio e metas.
- `docs/PRE_PROD_REBUILD_RUNBOOK.md` — gates operacionais de pré-produção.
