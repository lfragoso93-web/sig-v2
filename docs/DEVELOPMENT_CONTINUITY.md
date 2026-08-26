# Continuidade de desenvolvimento — SGI v2

> Documento obrigatório para iniciar ou retomar qualquer conversa de desenvolvimento. Atualizado em 18/08/2026.

## Contexto permanente

- Repositório: `lfragoso93-web/sig-v2`.
- Branch obrigatória: `stable-15jun`; nunca desenvolver diretamente na `main`.
- Confirmar o HEAD remoto e a árvore limpa antes de cada bloco.
- Dividir macroblocos em commits pequenos, independentes e rastreáveis.
- Antes de alterar, revisar Issue, arquitetura, contratos canônicos, consumidores e legado.
- Ao final informar resumo técnico, impacto arquitetural, arquivos, testes, SHA completo, Issue/documentação e próximo bloco.
- `goals` permanece fora da estabilização corrente e não recebe migration apenas para limpar Alembic.

## Baseline confirmado

- #247 concluída e promovida pela PR #281.
- PR #281 mergeada em `main` no commit `5ba685d962e2729844684c864cd71fdd1ab16d2f`.
- revisão de segurança da #269 recebeu bloco final pela PR #282.
- `main` pós-#282: `b45dc435b8f20b218ff1dfbdd9ab1c868817ff3f`.
- `stable-15jun` pós-#282, antes da sincronização documental desta retomada: `f36f02a32fcaf9345f98bb40f9065df7a2488101`.
- as árvores de `main` e `stable-15jun` eram equivalentes; a diferença era apenas o merge commit da PR #282.
- `test_ready=true`: permitido testar somente com dados fictícios/descartáveis enquanto os gates reais não autorizarem outra coisa.
- `ready_for_real_data=false`: usuários, carteiras, CSV, seeds e snapshots reais continuam bloqueados até decisão formal.

## Segurança

O bloco final da #269 tratou:

- path injection residual do serviço de backup;
- sanitização de sinks residuais de log;
- hardening da imagem runtime sem pip/setuptools;
- publicação SARIF do Trivy da imagem backend no workflow `Security deep scan`.

Evidências do bloco final:

- 1.611 testes backend aprovados e 35 ignorados;
- 105 testes dirigidos dos domínios afetados;
- flake8, mypy, compileall e `import app.main` aprovados;
- YAML do workflow e `git diff --check` aprovados;
- CI da PR #282 aprovado;
- CI global posterior na `stable-15jun` aprovou backend, frontend, `pip-audit`, `npm audit`, Gitleaks, Trivy filesystem e Hadolint.

O `Security deep scan` é semanal/manual. O GitHub App desta conversa não fornece inventário suficiente para afirmar execução pós-merge ou zeragem de todos os alertas externos. O baseline corrigido foi aceito operacionalmente para continuidade, mas scanners devem permanecer parte da verificação recorrente e nenhuma evidência ausente deve ser inventada.

## Arquitetura que deve ser preservada

- Runtime financeiro é DB-first; provider não participa de GETs/cálculos financeiros.
- Providers pertencem a bootstrap, ingestão, sincronização ou reconciliação explicitamente autorizados.
- Preços externos são persistidos antes do consumo financeiro.
- Ausência de preço/FX é explícita; não vira zero, preço médio, taxa `1.0` ou fallback silencioso.
- `summary.v2`, `rentabilidade.v2`, projetores de posição/custo e snapshots são contratos canônicos.
- Proventos pertencem ao ativo em `asset_dividends`; direitos por carteira são calculados sob demanda.
- Eventos corporativos pertencem ao ativo em `corporate_events`; transações históricas não são mutadas.
- Não reintroduzir `AppConfig`, `IRPFReport`, `Dividend/dividends`, routers placeholders ou materialização de Proventos por carteira.
- Tesouro/Renda Fixa devem preservar marcação a mercado; evolução de TWR pertence à #149.
- `goals` continua exceção deliberada de Alembic/MetaData até #246 + #57.

## Trabalho corrente — gate para TESTE REAL controlado

Nenhuma nova funcionalidade deve ser iniciada antes deste gate.

### Etapa 1 — revalidar blockers

Revisar no GitHub e no código:

- #227 — gate-mãe;
- #226 — duas execuções reais controladas de Proventos;
- #216 — gate agregado de seeds/bootstrap;
- #158 — rebuild/CSV/posições/snapshots/reconciliação.

Objetivo: identificar exatamente o que é obrigatório antes do teste real e separar:

- testes permitidos com dados fictícios/descartáveis;
- operações que exigem dados reais/autorização explícita;
- blockers que precisam de correção antes de qualquer carga.

### Etapa 2 — não contornar readiness

- não forçar `ready_for_real_data=true`;
- não alterar manualmente estados apenas para passar teste;
- não executar Proventos reais sem autorização vigente da #226;
- não contornar #216/#158;
- falhar fechado quando a arquitetura exigir.

### Etapa 3 — teste real auditável quando autorizado

Validar pelo menos:

1. infraestrutura: PostgreSQL, Redis, backend, frontend, migrations, espaço em disco, volumes, restart e persistência;
2. bootstrap: engine canônica, idempotência, locks, cobertura, Tesouro, benchmarks, FX, CRIPTO, Proventos, eventos e histórico;
3. carteira controlada: operações conhecidas, posição, custo médio, valuation, FX, snapshots, patrimônio, rentabilidade, IRPF, Tesouro e Renda Fixa;
4. reconciliação contra fonte/controladoria conhecida;
5. persistência após restart e Redis fail-open onde aplicável;
6. segurança runtime: logs, endpoints admin, debug, headers/rate limiting conforme arquitetura e scans disponíveis;
7. decisão explícita GO / NO-GO.

## Ordem posterior ao teste real

Se o gate permitir continuidade:

1. #150 — histórico persistido do IBOV;
2. #149 — TWR Tesouro/Renda Fixa;
3. #226 / #216 / #158 conforme pendências remanescentes e ordem operacional;
4. #272 — dívida física de `corporate_events` em bloco separado;
5. #246 + #57 — Metas + Análise de Carteira como macroprojeto único.

## Qualidade por macrobloco

Backend:

- pytest;
- compileall;
- import `app.main`;
- flake8;
- mypy;
- Alembic heads/current/check;
- fresh DB migration gate.

Frontend:

- `npm ci`;
- lint;
- typecheck;
- tests;
- build.

Segurança:

- `pip-audit`;
- `npm audit`;
- Trivy;
- Gitleaks HEAD/histórico quando aplicável;
- CodeQL/Code Scanning;
- Dependabot/Secret Scanning quando acessíveis.

Smoke:

- `docker compose ps`;
- `/health`;
- `/ready`;
- frontend HTTP;
- `git diff --check`;
- `git status --short`.

No host ARM/Linux, se Vitest paralelo gerar timeout artificial, executar serialmente com `--maxWorkers=1` e timeout aumentado apenas via CLI; não alterar timeout global do projeto para mascarar limitação de hardware.
