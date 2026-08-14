# Continuidade de desenvolvimento — SGI v2

> Documento obrigatório para iniciar ou retomar qualquer conversa de desenvolvimento. Atualizado em 14/08/2026.

## Contexto permanente

- Repositório: `lfragoso93-web/sig-v2`.
- Branch obrigatória: `stable-15jun`; nunca desenvolver diretamente na `main`.
- Confirmar o HEAD remoto e a árvore limpa antes de cada bloco.
- Dividir macroblocos em commits pequenos, independentes e rastreáveis.
- Antes de alterar, revisar Issue, arquitetura, contratos canônicos, consumidores e legado.
- Ao final informar resumo técnico, impacto arquitetural, arquivos, testes, SHA completo, Issue/documentação e próximo bloco.
- `goals` permanece fora da estabilização corrente e não recebe migration apenas para limpar Alembic.

## Baseline confirmado

- `main` = `stable-15jun` em `4ff76c4fe9f1738db9b392b3568fcb35f81185e7`.
- PR #271 mergeada; Issue #269 concluída.
- #268 concluída no checkpoint funcional `a8444b545a10aa7d48dd70f08a07e3fa386605d6`.
- `test_ready=true`: permitido testar somente com dados fictícios/descartáveis.
- `ready_for_real_data=false`: usuários, carteiras, CSV, seeds e snapshots reais continuam bloqueados.
- Snapshots de branches removidas preservados em:
  - `archive/recover-snapshot-b1c8080c`;
  - `archive/corporate-actions-5e110967`.
- Branches remanescentes: `main`, `stable-15jun` e cinco branches Dependabot sob triagem separada.

## Evidência do gate `test_ready`

No fechamento da #268:

- backend completo em Linux/Python 3.12: **1638 passed, 0 failed**;
- smoke HTTP e cleanup descartável aprovados;
- classes canônicas, BTC elegível e blockers CRIPTO exercitados;
- Alembic/drift gate, mypy, flake8, `compileall` e `app.main` aprovados;
- frontend lint, typecheck, 93 testes e build aprovados;
- CI aprovou backend, frontend, pip/npm audit, Trivy filesystem, Gitleaks e lint dos Dockerfiles;
- nenhum provider foi observado nos requests financeiros auditados.

A #269/#271 acrescentou hardening de SSRF, path injection, dependências, logs e imagem. O PR registrou backend **1.673 passed, 24 skipped**, frontend **93 testes**, `npm audit` sem vulnerabilidades e import/build aprovados.

## Arquitetura que deve ser preservada

- Runtime financeiro é DB-first; provider não participa de GETs/cálculos financeiros.
- Providers pertencem a bootstrap, ingestão, sincronização ou reconciliação explicitamente autorizados.
- Preços externos são persistidos antes do consumo financeiro.
- Ausência de preço/FX é explícita; não vira zero, preço médio, taxa `1.0` ou fallback silencioso.
- `summary.v2`, `rentabilidade.v2`, projetores de posição/custo e snapshots são contratos canônicos.
- Proventos pertencem ao ativo em `asset_dividends`; direitos por carteira são calculados sob demanda.
- Eventos corporativos pertencem ao ativo em `corporate_events`; transações históricas não são mutadas.
- Não reintroduzir `AppConfig`, `IRPFReport`, `Dividend/dividends` ou materialização de proventos por carteira.
- Tesouro/Renda Fixa devem preservar marcação a mercado; evolução de TWR pertence à #149.

## Trabalho corrente — #247

### 247-A — governança e documentação

- sincronizar README, ROADMAP, CHANGELOG, arquitetura e este documento;
- atualizar #227 para `test_ready=true` e baseline pós-#271;
- reclassificar Issues abertas e remover dependências/status obsoletos;
- consolidar #248/#250 no gate operacional da #227 quando o histórico estiver preservado;
- tratar #129 como residual da #247;
- auditar #83 contra a implementação existente antes de decidir fechamento;
- manter PRs/branches Dependabot como fila técnica separada.

### 247-B — posições DB-first

- confirmar consumidores de `position_service`;
- remover `quotes_service.get_current_price` do read path ou excluir o legado se estiver morto;
- preço ausente deve permanecer explícito, sem fallback por preço médio;
- testar endpoint, ausência, isolamento de provider e regressão.

### 247-C — snapshots de classe / FX DB-first

- migrar `portfolio_class_snapshot_service` de `fx_service` para leitor persistido;
- remover fallback de rede e USD-BRL `1.0`;
- reconciliar valores com tolerância financeira de R$ 0,01;
- não alterar TWR/valuation de Tesouro fora da #149.

### 247-D — Proventos e eventos

- auditar `proventos_daily_sync_service.py`, `asset_market_pipeline_service.py`, `dividend_backfill_service.py` e `run_proventos_sync.py`;
- eliminar ou confinar portas paralelas, preservando uma entrada canônica de bootstrap;
- usar a tag arquivada de corporate actions apenas como evidência para decisões de backlog;
- testar locks, transação, idempotência e ausência de consumers/imports legados.

### 247-E — superfícies sensíveis e frontend legado

- restringir/remover o router de debug conforme ambiente e autenticação;
- remover `frontend/src/App.tsx` somente após confirmar ausência de imports;
- revisar placeholder de Análise, aliases, redirects, módulos órfãos e catches amplos;
- preservar #246 + #57 como macroprojeto bloqueado.

### 247-F — gate global

- backend: pytest completo, flake8, mypy, compile/import e Alembic/drift;
- frontend: lint, typecheck, testes e build;
- segurança: npm/pip audit, Gitleaks e Trivy;
- smoke HTTP fictício, cleanup e inspeção de provider;
- concluir #247/#129 e preparar PR `stable-15jun` → `main` somente com tudo verde.

## Ordem após a sanitização

1. #150 — histórico persistido do IBOV.
2. #149 — TWR de Tesouro Direto/Renda Fixa com marcação a mercado persistida.
3. #226 — duas execuções reais controladas de Proventos, somente com autorização operacional específica.
4. #216 — fechar gate agregado de seeds/bootstrap.
5. #158 — CSV, posições, snapshots e reconciliação da primeira base real.
6. Decidir formalmente `ready_for_real_data=true` na #227.
7. #253 — Central de Bootstrap SuperAdmin.
8. #246 + #57 — Metas + Análise como macroprojeto único.

## Prompt mínimo para retomada

```text
@GitHub Continue o SGI v2 seguindo docs/DEVELOPMENT_CONTINUITY.md.

Repo: lfragoso93-web/sig-v2
Branch exclusiva: stable-15jun
Baseline: 4ff76c4fe9f1738db9b392b3568fcb35f81185e7
Gate-mãe: #227
Trabalho atual: #247

Estado:
- test_ready=true;
- ready_for_real_data=false;
- preservar DB-first e contratos canônicos;
- commits pequenos e documentação/Issues vivas.

Próxima ação: continuar do primeiro sub-bloco pendente da #247.
```
