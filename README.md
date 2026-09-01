# SGI v2 — Sistema de Gestão de Investimentos

Plataforma pessoal para acompanhamento, consolidação e análise de investimentos, com backend FastAPI e frontend React + TypeScript.

A branch de desenvolvimento é `stable-15jun`. A promoção para `main` ocorre exclusivamente por Pull Request após validação integral e sincronização da documentação viva.

## Status atual — 27/08/2026

Atualização de 01/09/2026: a PR #302 foi mergeada em `main` pelo commit `7861268a2528d80e8c23dfc55f7b0800402abc6d`. O desenvolvimento continua em `stable-15jun` no baseline `2c9358629b3e5e9206a365ebeac45f9272dfd48e`; `main` está um commit à frente apenas pelo merge commit da #302.

O SGI v2 concluiu a sanitização arquitetural da Issue #247 e o bloco final de segurança da Issue #269. Desde então, o foco migrou da construção da base para **certificação operacional e preparação para testes integrados**.

O ambiente OCI de laboratório já está funcional e foi usado para validar build/runtime, contratos de bootstrap e smoke HTTP descartável. As PRs #290, #291 e #292 consolidaram esse avanço, sem executar seeds reais e sem promover o ambiente para dados reais.

A Issue #227 permanece como gate-mãe para dados reais.

- `test_ready=true`: permanece válido para testes controlados com usuários, carteiras e dados fictícios/descartáveis.
- `ready_for_real_data=false`: permanece obrigatório; nenhuma flag deve ser forçada manualmente para executar teste ou carga real.

Baseline vigente no início deste rebaseline:

- `stable-15jun`: `a889edb6bbbb78feb7787c21b3439a0b835b73c6`;
- `main`: `3eeca232a8627f4562544739112d1dde82b879fb`;
- `main` contém a PR #292; `stable-15jun` já avançou com pequenos blocos posteriores de documentação e hardening do smoke.

### Evidências OCI já obtidas

- stack Docker validada em ARM64 para o alvo Ampere A1;
- laboratório OCI descartável disponível para validações sem dados reais;
- frontend production build aprovado no lab;
- hostname público via Cloudflare Tunnel validado com HTTP/2 200;
- smoke OCI aprovado;
- suites de contrato executadas sem seeds reais:
  - FX/Macro/Tesouro: 81 aprovados, 1 ignorado;
  - B3/Asset Bootstrap/System Bootstrap: 70 aprovados;
  - Proventos: 93 aprovados, 8 ignorados;
- wrapper de validação de contratos publicado pela PR #291;
- smoke HTTP descartável endurecido pela PR #292;
- usuário comum explicitamente bloqueado (`403`) em `/api/v1/admin/bootstrap/status` no SHA `a889edb6bbbb78feb7787c21b3439a0b835b73c6`.

Nenhuma dessas evidências autoriza dados reais. O próximo macrobloco continua sendo a certificação controlada dos gates #227, #226, #216 e #158.

A convergência Alembic ↔ MetaData da Issue #241 permanece concluída para todos os domínios estabilizados. O único diff deliberadamente preservado é `goals`, que não deve receber migration antes do redesenho conjunto de Metas e Análise de Carteira (#246 + #57).

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

A seleção é dinâmica: um ativo pode entrar ou sair do universo em bootstrap futuro conforme o ranking de market cap. A #267 certificou 55 candidatos, 42 ativos financeiros e 13 blockers preservados. `ready_for_real_data` continua `false` até certificação operacional posterior.

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

Os direitos de Proventos são calculados sob demanda a partir do catálogo global persistido e da posição histórica; nenhuma leitura financeira materializa direitos por carteira.

`ready_for_real_data` permanece `false` até todos os domínios obrigatórios e gates de certificação estarem concluídos.

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

### Agora — certificação para TESTES integrados

1. Sincronizar documentação viva e Issues com o baseline OCI pós-PRs #290/#291/#292.
2. Executar qualidade completa e smoke no lab com dados fictícios/descartáveis.
3. Validar restart, persistência, volumes, migrations e Redis fail-open.
4. Validar `system-bootstrap.v4` e seus contratos sem contornar gates de dados reais.
5. Revalidar #227, #226, #216 e #158.
6. Somente quando houver autorização operacional, executar as duas rodadas reais controladas de Proventos (#226).
7. Fechar o gate agregado (#216), retomar rebuild/CSV/posições/snapshots (#158) e reconciliar os resultados.
8. Produzir decisão explícita GO / NO-GO para `ready_for_real_data`.

### Depois — performance e benchmarks

9. Materializar histórico persistido do IBOV (#150).
10. Implementar TWR dedicado de Tesouro Direto e Renda Fixa (#149).
11. Reconciliar snapshots e rentabilidade quando necessário.

### Dívidas estruturais separadas

12. Tratar #272 em janela própria para contração física de aliases/colunas legadas de `corporate_events`.

### Próxima grande fase funcional

13. Redesenhar Metas + Análise de Carteira como um único macroprojeto (#246 + #57), definindo domínio e contratos antes de schema/API/frontend.

## Estado operacional

- `system-bootstrap.v4` é a porta única de bootstrap e registra catálogo, históricos, Tesouro, benchmarks, FX, Proventos e eventos corporativos sob contratos canônicos.
- Proventos permanecem governados pela #226 para execução real.
- `test_ready=true` foi certificado pela #268 e recebeu novos smokes OCI pós-certificação.
- Depois do bootstrap certificado, chamadas externas recorrentes ficam limitadas a preço intraday e fechamento diário.
- CRUD de transações não dispara ingestão externa automática.
- Rebuilds permanecem operações explícitas; não pertencem a requests comuns.
- Importação CSV real, criação de carteiras reais e snapshots de produção continuam suspensos pela #227 até decisão formal final.
- O diff remanescente do `alembic check` está limitado a `goals` e é exceção deliberada rastreada pela #246.

## Segurança

O bloco final da #269 foi promovido pela PR #282. O CI correspondente foi aprovado e o runtime backend preserva o hardening de path/logs e a remoção de pip/setuptools. O workflow `Security deep scan` permanece semanal/manual e deve continuar sendo usado como verificação periódica; não se deve inferir execução de scanners que não tenham evidência explícita.

## PRs de dependências

Em 01/09/2026 existem 7 PRs Dependabot abertas contra `main`: #295, #296, #297, #298, #299, #300 e #301. Elas devem ser avaliadas em blocos próprios, sem merge automático e sem PR nova para microblocos.

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
- `docs/deployment/oci.md` — histórico e decisões do ambiente OCI.
- `docs/PROVIDER_ACCESS_POLICY_2026-08.md` — política de acesso a providers.
- `docs/ROUTER_ENDPOINT_AUDIT_2026-08.md` — auditoria das superfícies HTTP.
- `docs/DIVIDENDS_CANONICAL_ARCHITECTURE.md` — arquitetura canônica de Proventos.
- `docs/ALEMBIC_METADATA_DRIFT_INVENTORY_2026-08.md` — inventário final da convergência e exceção `goals`.
- `docs/PRE_PROD_REBUILD_RUNBOOK.md` — gates operacionais de pré-produção.
