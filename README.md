# SGI v2 — Sistema de Gestão de Investimentos

Plataforma pessoal para acompanhamento, consolidação e análise de investimentos, com backend FastAPI e frontend React + TypeScript.

A branch de desenvolvimento é `stable-15jun`. A promoção para `main` ocorre exclusivamente por Pull Request após validação integral e sincronização da documentação viva.

## Status atual — 08/08/2026

O SGI v2 está em **estabilização arquitetural e certificação do bootstrap inicial antes da próxima fase funcional**.

A Issue #227 é o gate-mãe que bloqueia dados reais até a certificação estrutural. A Issue #247 executa a auditoria de legado, serviços, routers, endpoints e integrações. A #248 coordena a fronteira de providers/readiness e a #250 executa o orquestrador global.

A convergência Alembic ↔ MetaData da Issue #241 foi concluída para todos os domínios estabilizados. O único diff deliberadamente preservado é `goals`, que não deve receber migration antes do redesenho conjunto de Metas e Análise de Carteira (#246 + #57).

### Regra canônica de dados externos

O SGI v2 adota uma fronteira explícita entre **bootstrap de dados** e **runtime financeiro**:

- antes de cadastrar carteiras reais, o ambiente deve executar um bootstrap idempotente que carregue e persista o catálogo e todo o histórico necessário ao funcionamento do sistema;
- esse bootstrap alimenta o banco com ativos/metadados, históricos, Proventos, eventos corporativos, Tesouro, benchmarks, câmbio e demais séries necessárias;
- depois que o ambiente estiver certificado e operacional, requests funcionais e cálculos financeiros consomem somente dados persistidos;
- consultas externas recorrentes em runtime ficam restritas a **preço intraday** e **preço oficial/de fechamento do dia**, que devem ser persistidos antes de alimentar os contratos financeiros;
- busca de ativos, detalhes, relatórios, posições, rentabilidade, IRPF, Proventos e demais módulos não consultam provedores externos diretamente.

A disponibilização para criação/importação de carteiras reais só ocorre depois que o bootstrap inicial estiver concluído e validado.

### Bootstrap global atual

O contrato corrente é `system-bootstrap.v3`.

Etapas já registradas no orquestrador único:

- catálogo de ativos;
- catálogo, reconciliação e histórico do Tesouro;
- histórico global de preços;
- benchmarks;
- câmbio USD-BRL por PTAX oficial, reutilizando o seed auditável da #217;
- Proventos globais em `asset_dividends`, reutilizando `pre-prod-dividends-seed.v2` sob gate explícito da #226.

Eventos corporativos são o próximo domínio estrutural a incorporar. A etapa de Proventos não executa providers sem opt-in `SGI_BOOTSTRAP_ENABLE_DIVIDENDS=true`; esse opt-in técnico não substitui a autorização operacional exigida pela #226.

O bootstrap possui identidade auditável compartilhada (`run_id`, `stable-15jun`, SHA completo). O SHA é obrigatório no disparo administrativo e pode ser fornecido por `SGI_BOOTSTRAP_COMMIT_SHA` no startup automático.

`ready_for_real_data` permanece `false` até todos os domínios obrigatórios e gates de certificação estarem concluídos.

### Qualidade validada

Último checkpoint certificado localmente pelo usuário: HEAD `0e8d96c081a0e788a9edcf69901a134b29b7f696`.

- Build Docker aprovado.
- `compileall` aprovado.
- **22/22 testes** do checkpoint de bootstrap/FX/readiness aprovados.
- Import integral de `app.main` aprovado.
- HEAD local igual ao remoto esperado.

As alterações posteriores que registram Proventos no `system-bootstrap.v3` permanecem pendentes de validação local.

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

### Agora — bootstrap e auditoria estrutural

1. Validar localmente o `system-bootstrap.v3` com o novo gate de Proventos (#248/#250/#226).
2. Incorporar eventos corporativos globais ao bootstrap reutilizando o motor canônico e preservando a #129.
3. Continuar auditoria de routers, serviços, endpoints, aliases e integrações (#247).
4. Eliminar chamadas externas fora da fronteira canônica de bootstrap/preços.
5. Certificar o bootstrap inicial completo antes da retomada de dados reais.

### Depois — performance e benchmarks

6. Materializar histórico persistido do IBOV (#150).
7. Implementar TWR dedicado de Tesouro Direto e Renda Fixa (#149).

### Bloqueado até certificação estrutural e bootstrap

8. Executar as duas rodadas reais controladas de Proventos (#226), somente na janela autorizada.
9. Fechar o gate agregado de seeds/bootstrap (#216).
10. Retomar rebuild, CSV, posições, snapshots e reconciliação (#158).
11. Somente então liberar criação/importação de carteiras reais.

### Próxima grande fase funcional

12. Redesenhar Metas + Análise de Carteira como um único macroprojeto (#246 + #57).

## Estado operacional

- Dados históricos e catálogos existentes continuam sendo persistidos no banco.
- `system-bootstrap.v3` é a porta única de bootstrap e já registra FX e Proventos sob seus contratos canônicos.
- Proventos permanecem bloqueados para execução real até autorização da #226.
- Eventos corporativos ainda precisam ser integrados ao bootstrap global.
- Depois do bootstrap certificado, chamadas externas recorrentes ficam limitadas a preço intraday e fechamento diário.
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