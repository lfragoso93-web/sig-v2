# SGI v2 — Sistema de Gestão de Investimentos

Plataforma pessoal para acompanhamento, consolidação e análise de investimentos, com backend FastAPI e frontend React + TypeScript.

A branch de desenvolvimento é `stable-15jun`. A promoção para `main` ocorre exclusivamente por Pull Request após validação integral e sincronização da documentação viva.

## Status atual — 18/08/2026

O SGI v2 concluiu a sanitização arquitetural da Issue #247 e promoveu esse baseline para `main` pela PR #281. Em seguida, a revisão de segurança da Issue #269 recebeu um bloco final pela PR #282, com hardening de backup/path, sanitização residual de logs e publicação SARIF do Trivy da imagem backend.

A Issue #227 permanece como gate-mãe para dados reais.

- `test_ready=true`: permanece válido para testes controlados com usuários, carteiras e dados fictícios/descartáveis.
- `ready_for_real_data=false`: permanece obrigatório; nenhuma flag deve ser forçada manualmente para executar teste ou carga real.

Baseline vigente:

- `stable-15jun`: `f36f02a32fcaf9345f98bb40f9065df7a2488101`;
- `main`: `b45dc435b8f20b218ff1dfbdd9ab1c868817ff3f`;
- as árvores são equivalentes; a diferença é apenas o merge commit da PR #282.

O próximo macrobloco não é funcional: é o gate para o TESTE REAL controlado. Antes de qualquer carga real, #226, #216 e #158 devem ser revalidadas contra o baseline pós-#281/#282. Se houver blocker formal, ele deve ser resolvido sem contorno e em microbloco próprio.

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

### Agora — gate para TESTE REAL controlado

1. Revalidar #227, #226, #216 e #158 contra o baseline pós-#281/#282.
2. Confirmar quais gates permitem teste com dados fictícios e quais exigem execução real autorizada.
3. Não forçar `ready_for_real_data=true`.
4. Resolver blockers formais em Issues/microblocos próprios.
5. Quando autorizado, executar teste real auditável de infraestrutura, bootstrap, dados, reconciliação, persistência e segurança.
6. Produzir decisão explícita GO / NO-GO.

### Depois — performance e benchmarks

7. Materializar histórico persistido do IBOV (#150).
8. Implementar TWR dedicado de Tesouro Direto e Renda Fixa (#149).
9. Reconciliar snapshots e rentabilidade quando necessário.

### Cadeia operacional para dados reais

10. Executar as duas rodadas reais controladas de Proventos (#226), se ainda forem requisito após a auditoria do gate.
11. Fechar o gate agregado de seeds/bootstrap (#216).
12. Retomar rebuild, CSV, posições, snapshots e reconciliação (#158).
13. Somente então decidir `ready_for_real_data=true`.

### Dívidas estruturais separadas

14. Tratar #272 em janela própria para contração física de aliases/colunas legadas de `corporate_events`.

### Próxima grande fase funcional

15. Redesenhar Metas + Análise de Carteira como um único macroprojeto (#246 + #57), definindo domínio e contratos antes de schema/API/frontend.

## Estado operacional

- `system-bootstrap.v4` é a porta única de bootstrap e registra catálogo, históricos, Tesouro, benchmarks, FX, Proventos e eventos corporativos sob contratos canônicos.
- Proventos permanecem governados pela #226 para execução real.
- `test_ready=true` foi certificado pela #268 no SHA `a8444b545a10aa7d48dd70f08a07e3fa386605d6`.
- Depois do bootstrap certificado, chamadas externas recorrentes ficam limitadas a preço intraday e fechamento diário.
- CRUD de transações não dispara ingestão externa automática.
- Rebuilds permanecem operações explícitas; não pertencem a requests comuns.
- Importação CSV real, criação de carteiras reais e snapshots de produção continuam suspensos pela #227 até decisão formal final.
- O diff remanescente do `alembic check` está limitado a `goals` e é exceção deliberada rastreada pela #246.

## Segurança

O bloco final da #269 foi promovido pela PR #282. O CI correspondente foi aprovado e o runtime backend preserva o hardening de path/logs e a remoção de pip/setuptools. O workflow `Security deep scan` permanece semanal/manual e deve continuar sendo usado como verificação periódica; não se deve inferir execução de scanners que não tenham evidência explícita.

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
- `docs/ROUTER_ENDPOINT_AUDIT_2026-08.md` — auditoria das superfícies HTTP.
- `docs/DIVIDENDS_CANONICAL_ARCHITECTURE.md` — arquitetura canônica de Proventos.
- `docs/ALEMBIC_METADATA_DRIFT_INVENTORY_2026-08.md` — inventário final da convergência e exceção `goals`.
- `docs/PRE_PROD_REBUILD_RUNBOOK.md` — gates operacionais de pré-produção.
