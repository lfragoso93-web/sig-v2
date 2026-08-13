# SGI v2 — Sistema de Gestão de Investimentos

Plataforma pessoal para acompanhamento, consolidação e análise de investimentos, com backend FastAPI e frontend React + TypeScript.

A branch de desenvolvimento é `stable-15jun`. A promoção para `main` ocorre exclusivamente por Pull Request após validação integral e sincronização da documentação viva.

## Status atual — 11/08/2026

O SGI v2 está em **estabilização arquitetural e certificação do bootstrap inicial antes da próxima fase funcional**.

A Issue #227 é o gate-mãe que bloqueia dados reais até a certificação estrutural. A Issue #247 executa a auditoria de legado, serviços, routers, endpoints e integrações. A #248 coordena a fronteira de providers/readiness e a #250 executa o orquestrador global. A #267 formaliza o novo universo CRIPTO suportado.

A convergência Alembic ↔ MetaData da Issue #241 foi concluída para todos os domínios estabilizados. O único diff deliberadamente preservado é `goals`, que não deve receber migration antes do redesenho conjunto de Metas e Análise de Carteira (#246 + #57).

### Regra canônica de dados externos

O SGI v2 adota uma fronteira explícita entre **bootstrap de dados** e **runtime financeiro**:

- antes de cadastrar carteiras reais, o ambiente deve executar um bootstrap idempotente que carregue e persista o catálogo e todo o histórico necessário ao funcionamento do sistema;
- esse bootstrap alimenta o banco com ativos/metadados, históricos, Proventos, eventos corporativos, Tesouro, benchmarks, câmbio e demais séries necessárias;
- depois que o ambiente estiver certificado e operacional, requests funcionais e cálculos financeiros consomem somente dados persistidos;
- consultas externas recorrentes em runtime ficam restritas a **preço intraday** e **preço oficial/de fechamento do dia**, que devem ser persistidos antes de alimentar os contratos financeiros;
- busca de ativos, detalhes, relatórios, posições, rentabilidade, IRPF, Proventos e demais módulos não consultam provedores externos diretamente.

A disponibilização para criação/importação de carteiras reais só ocorre depois que o bootstrap inicial estiver concluído e validado.

### Universo CRIPTO suportado

O catálogo amplo de um provider **não** equivale ao universo operacional do SGI. A partir da #267, CRIPTO segue um contrato explícito de relevância de mercado:

- fonte de ranking: CoinGecko `/coins/markets`, ordenado por capitalização de mercado;
- limite: Top 100 por `market_cap_rank`;
- elegibilidade operacional: interseção entre o Top 100 CoinGecko e os símbolos disponíveis no catálogo CRIPTO do provedor de mercado integrado;
- o provedor de mercado integrado continua sendo a fonte de disponibilidade/cotação do SGI; CoinGecko é usado somente para definir o ranking de relevância no bootstrap;
- ativos CRIPTO persistidos anteriormente fora do universo suportado não são apagados nem têm lifecycle falsificado;
- seed, bootstrap histórico e readiness CRIPTO consideram somente o universo suportado;
- ativos fora do universo não devem bloquear a certificação CRIPTO.

A seleção é dinâmica: um ativo pode entrar ou sair do universo em bootstrap futuro conforme o ranking de market cap. `ready_for_real_data` continua `false` até certificação operacional posterior.

### Bootstrap global atual

O contrato corrente é `system-bootstrap.v4`.

Etapas já registradas no orquestrador único:

- catálogo de ativos, com CRIPTO limitado ao universo Top 100 suportado;
- catálogo, reconciliação e histórico do Tesouro;
- histórico global de preços, com CRIPTO limitado ao mesmo universo suportado;
- benchmarks;
- câmbio USD-BRL por PTAX oficial, reutilizando o seed auditável da #217;
- Proventos globais em `asset_dividends`, reutilizando `pre-prod-dividends-seed.v2` sob gate explícito da #226;
- eventos corporativos globais em `corporate_events`, por wrapper dedicado que lê o catálogo persistido, usa advisory lock transacional e delega exclusivamente a `sync_corporate_events_for_asset`.

Proventos não executam providers sem opt-in `SGI_BOOTSTRAP_ENABLE_DIVIDENDS=true`; esse opt-in técnico não substitui a autorização operacional exigida pela #226. Eventos corporativos também permanecem fail-closed sem `SGI_BOOTSTRAP_ENABLE_CORPORATE_EVENTS=true`.

Os direitos de Proventos são calculados sob demanda a partir do catálogo global
persistido e da posição histórica; nenhuma leitura financeira materializa
direitos por carteira.

`ready_for_real_data` permanece `false` até todos os domínios obrigatórios e gates de certificação estarem concluídos.

### Evidência CRIPTO anterior ao corte Top 100

A auditoria BC/BD no universo amplo de 481 ativos foi certificada em `9772b8c2bdb9875d85abc4a72ed0bebea39c222e`:

- 369 `HISTORY_START_EXHAUSTED`;
- 87 `HISTORY_START_COMPLEMENT_GAPPED`;
- 14 `HISTORY_START_SHALLOW_UNAVAILABLE`;
- 10 `HISTORY_START_SHALLOW_VERIFIED`;
- 1 `HISTORY_UNAVAILABLE` (`XUSD`);
- zero duplicidades;
- 88 seams bloqueantes;
- 71 dos 87 gaps excediam 365 dias.

Esse diagnóstico motivou a separação entre catálogo descoberto e universo suportado. Esses estados antigos permanecem auditáveis, mas só os ativos que estiverem no universo Top 100 suportado devem participar do novo readiness CRIPTO.

## Arquitetura resumida

```text
bootstrap inicial / sincronizadores operacionais
        ↓
catálogo suportado + históricos + eventos + taxas persistidos
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

Princípios: DB-first, fonte oficial primeiro, bootstrap idempotente, universo operacional explícito, ausência não convertida em zero, contratos financeiros únicos e nenhuma chamada a provedor durante cálculos financeiros.

## Ordem canônica de trabalho

### Agora — bootstrap e auditoria estrutural

1. Validar localmente o contrato Top 100 CRIPTO da #267, incluindo ranking, interseção com o catálogo de mercado, seed, bootstrap histórico e readiness.
2. Reexecutar a auditoria/readiness CRIPTO sobre o universo suportado e registrar os findings residuais reais.
3. Validar localmente o `system-bootstrap.v4`, incluindo os gates de Proventos e eventos corporativos (#248/#250/#226/#254).
4. Reconciliar os critérios finais de cobertura, idempotência e readiness do bootstrap completo.
5. Continuar auditoria de routers, serviços, endpoints, aliases e integrações (#247/#129).
6. Certificar o bootstrap inicial completo antes da retomada de dados reais.

### Depois — performance e benchmarks

7. Materializar histórico persistido do IBOV (#150).
8. Implementar TWR dedicado de Tesouro Direto e Renda Fixa (#149).

### Bloqueado até certificação estrutural e bootstrap

9. Executar as duas rodadas reais controladas de Proventos (#226), somente na janela autorizada.
10. Fechar o gate agregado de seeds/bootstrap (#216).
11. Retomar rebuild, CSV, posições, snapshots e reconciliação (#158).
12. Somente então liberar criação/importação de carteiras reais.

### Próxima grande fase funcional

13. Redesenhar Metas + Análise de Carteira como um único macroprojeto (#246 + #57).

## Estado operacional

- Dados históricos e catálogos existentes continuam sendo persistidos no banco.
- CRIPTO passa a possuir universo operacional Top 100 por market cap, cruzado com disponibilidade no catálogo de mercado integrado.
- Registros CRIPTO legados fora desse universo são preservados para auditoria e não bloqueiam o novo readiness por princípio.
- `system-bootstrap.v4` é a porta única de bootstrap e já registra FX, Proventos e eventos corporativos sob seus contratos canônicos.
- Proventos permanecem bloqueados para execução real até autorização da #226.
- Eventos corporativos estão estruturalmente integrados, mas permanecem opt-in e ainda pendem de validação local integrada/certificação final.
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
- `docs/PROVIDER_ACCESS_POLICY_2026-08.md` — política de acesso a providers.
- `docs/ROUTER_ENDPOINT_AUDIT_2026-08.md` — auditoria corrente das superfícies HTTP.
- `docs/DIVIDENDS_CANONICAL_ARCHITECTURE.md` — arquitetura canônica de Proventos.
- `docs/ALEMBIC_METADATA_DRIFT_INVENTORY_2026-08.md` — inventário final da convergência e exceção `goals`.
- `docs/PRE_PROD_REBUILD_RUNBOOK.md` — gates operacionais de pré-produção.
