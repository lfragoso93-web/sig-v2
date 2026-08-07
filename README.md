# SGI v2 — Sistema de Gestão de Investimentos

Plataforma pessoal para acompanhamento, consolidação e análise de investimentos, com backend FastAPI e frontend React + TypeScript.

A branch de desenvolvimento é `stable-15jun`. A promoção para `main` ocorre exclusivamente por Pull Request após validação integral e sincronização da documentação viva.

## Status atual — 07/08/2026

O SGI v2 está em **estabilização arquitetural e auditoria antes da próxima fase funcional**.

A Issue #227 é o gate-mãe que bloqueia dados reais até a certificação estrutural. A Issue #247 executa a auditoria atual de legado, serviços, routers, endpoints e integrações.

A convergência Alembic ↔ MetaData da Issue #241 foi concluída para todos os domínios estabilizados. O único diff deliberadamente preservado é `goals`, que não deve receber migration antes do redesenho conjunto de Metas e Análise de Carteira (#246 + #57).

### Regra canônica de dados externos

O SGI v2 passa a adotar uma fronteira explícita entre **bootstrap de dados** e **runtime financeiro**:

- antes de cadastrar carteiras reais, o ambiente deve executar um bootstrap idempotente que carregue e persista o catálogo e todo o histórico necessário ao funcionamento do sistema;
- esse bootstrap deve alimentar o banco com ativos/metadados, históricos, Proventos, eventos corporativos, Tesouro, benchmarks, câmbio e demais séries necessárias;
- depois que o ambiente estiver certificado e operacional, requests funcionais e cálculos financeiros devem consumir somente dados persistidos;
- consultas externas recorrentes em runtime ficam restritas a **preço intraday** e **preço oficial/de fechamento do dia**, que devem ser persistidos antes de alimentar os contratos financeiros;
- busca de ativos, detalhes, relatórios, posições, rentabilidade, IRPF, Proventos e demais módulos não devem consultar provedores externos diretamente.

A disponibilização para criação/importação de carteiras reais só ocorre depois que o bootstrap inicial estiver concluído e validado.

### Qualidade validada

Baseline certificado localmente no HEAD `08414af3a7b570ae9753e83ba5eecf2c17f20e42`:

- Build Docker aprovado.
- `compileall` aprovado.
- 7 testes do checkpoint de auditoria aprovados.
- Import integral de `app.main` aprovado.
- Working tree limpa.

### Entregas consolidadas

- Arquitetura DB-first e contratos `summary.v2` e `rentabilidade.v2`.
- Valuation canônico por classe, snapshots patrimoniais e reconciliação financeira.
- Histórico B3/COTAHIST, Tesouro oficial, benchmarks e câmbio persistidos.
- Leitura pública USD/BRL exclusivamente por `fx_rates`, alinhado ao MetaData/Alembic.
- Proventos globais em `asset_dividends`, com direitos de carteira calculados sob demanda.
- Motor canônico de eventos corporativos e projeção histórica compartilhada de posição, custo e resultado realizado.
- IRPF anual canônico, frontend e exportações sem persistência de `IRPFReport` legado.
- Transactions alinhado ao contrato físico migrado e sem sincronização externa automática no CRUD.
- GETs financeiros de histórico de preços e posições endurecidos como DB-first.
- Backfill público de performance removido; rebuilds permanecem operações internas explícitas.
- Alembic endurecido com gates contra autogenerate monolítico e remoções acidentais.

## Arquitetura resumida

```text
bootstrap inicial / sincronizadores operacionais
        ↓
catálogo + históricos + eventos + taxas persistidos
        ↓
transactions + fixed_income_investments + corporate_events
        ↓
projeções canônicas de posição, custo e realizações
        ↓
valuation dedicado por classe
        ↓
PortfolioSnapshot + PortfolioClassSnapshot
        ↓
summary.v2 / rentabilidade.v2 / leitores históricos
        ↓
Resumo / Patrimônio / Rentabilidade / Proventos / IRPF
```

No runtime normal, provedores externos só participam da captura de preço intraday e preço de fechamento diário; esses valores são persistidos antes de serem consumidos pelos contratos financeiros.

Metas e Análise de Carteira estão fora do conjunto de contratos funcionais estabilizados neste momento. O redesenho será tratado como um único macroprojeto pelas Issues #246 e #57 somente depois da estabilização definitiva da base.

Princípios: DB-first, fonte oficial primeiro, bootstrap idempotente, ausência não convertida em zero, contratos financeiros únicos e nenhuma chamada a provedor durante cálculos financeiros.

## Ordem canônica de trabalho

### Agora — auditoria estrutural

1. Continuar auditoria de routers, serviços, endpoints, aliases e integrações (#247).
2. Eliminar chamadas externas fora da fronteira canônica de bootstrap/preços.
3. Confirmar o estado real de consumidores restantes de eventos corporativos (#129) e itens de provedores relacionados (#130/#127).
4. Desenhar e certificar o bootstrap inicial completo antes da retomada de dados reais.

### Depois — performance e benchmarks

5. Materializar histórico persistido do IBOV (#150).
6. Implementar TWR dedicado de Tesouro Direto e Renda Fixa (#149).

### Bloqueado até certificação estrutural e bootstrap

7. Executar as duas rodadas reais controladas de Proventos (#226).
8. Fechar o gate agregado de seeds/bootstrap (#216).
9. Retomar rebuild, CSV, posições, snapshots e reconciliação (#158).
10. Somente então liberar criação/importação de carteiras reais.

### Próxima grande fase funcional

11. Redesenhar Metas + Análise de Carteira como um único macroprojeto (#246 + #57).

## Estado operacional

- Dados históricos e catálogos existentes continuam sendo persistidos no banco.
- O próximo desenho operacional deve transformar a subida inicial do ambiente em um bootstrap completo, idempotente e certificável antes de liberar uso real.
- Depois do bootstrap, chamadas externas recorrentes ficam limitadas a preço intraday e fechamento diário.
- CRUD de transações não dispara ingestão externa automática.
- Rebuilds permanecem operações explícitas; não pertencem a requests comuns.
- Importação CSV real, criação de carteiras reais e snapshots de produção continuam suspensos pela #227 até o bootstrap/gates serem certificados.
- O diff remanescente do `alembic check` está limitado a `goals` e é exceção deliberada rastreada pela #246.

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
- `docs/ROUTER_ENDPOINT_AUDIT_2026-08.md` — auditoria corrente das superfícies HTTP.
- `docs/DIVIDENDS_CANONICAL_ARCHITECTURE.md` — arquitetura canônica de Proventos.
- `docs/ALEMBIC_METADATA_DRIFT_INVENTORY_2026-08.md` — inventário final da convergência e exceção `goals`.
- `docs/PRE_PROD_REBUILD_RUNBOOK.md` — gates operacionais de pré-produção.
