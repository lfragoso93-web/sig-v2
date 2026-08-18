# SGI v2 — checkpoint de estabilização — 2026-08-18

## Estado canônico

A Issue #247 concluiu a sanitização arquitetural pós-convergência na `stable-15jun`.

HEAD certificado antes deste checkpoint: `8d82d84ec35387b53abbcbec49b485184ec696d0`.

A aplicação permanece com `test_ready=true` para validação controlada com dados fictícios e `ready_for_real_data=false` até a cadeia operacional #226 → #216 → #158 ser concluída sob o gate-mãe #227.

## Blocos concluídos pela #247

- governança e documentação pós-#271;
- posições e read paths residuais consolidados em DB-first;
- snapshots de classe/FX sem provider/fallback em request financeiro;
- saneamento funcional de Proventos e eventos corporativos;
- fechamento da #129 e separação da dívida física de schema na #272;
- remoção de tooling histórico de IRPF e eventos corporativos;
- remoção de superfícies/routers/placeholders sem consumidores comprovados;
- consolidação da superfície única de bootstrap administrativo;
- remoção do placeholder HTTP 501 de Análise, preservando #246 + #57 como macroprojeto futuro;
- gates estruturais contra reintrodução de legado;
- higiene de repositório e scanners de segurança locais.

## Gate global 247-F

### Backend

- suíte completa no último baseline funcional: `1612 passed, 35 skipped, 0 failed`;
- `python -m compileall -q app tests`: aprovado;
- `import app.main`: OK;
- `flake8`: aprovado;
- `mypy`: `0 issues` em 326 arquivos.

### Frontend

- lint: aprovado;
- typecheck: aprovado;
- Vitest serial no host ARM/Linux: `36/36` arquivos e `130/130` testes;
- build de produção: aprovado.

### Dependências e segurança

- `npm audit`: 0 vulnerabilidades;
- `pip-audit`: nenhuma vulnerabilidade conhecida;
- Trivy HIGH/CRITICAL: 0 findings em `backend/requirements.txt` e `frontend/package-lock.json`;
- Gitleaks no HEAD: 0 leaks;
- Gitleaks no histórico completo: 0 leaks em 3288 commits;
- `.abacusai/config.json` removido por ser metadata de ferramenta externa sem função no SGI;
- `.gitleaks.toml` usa regras padrão e allowlist cirúrgica apenas para identificadores públicos de domínio que geravam falsos positivos.

### Banco e Alembic

- `alembic heads` == `alembic current` == `20260813_rate_history_metadata`;
- `alembic check` diverge somente por `goals`, exceção deliberada fora da estabilização atual;
- nenhuma migration de `goals` deve ser criada antes do redesenho conjunto #246 + #57.

### Smoke local Linux/Docker

- PostgreSQL: healthy;
- Redis: healthy;
- backend: healthy;
- `/health`: HTTP 200;
- frontend: HTTP 200;
- `/ready`: HTTP 503 esperado enquanto `ENABLE_BOOT_MARKET_SYNC=false` e `ready_for_real_data=false`.

## Dívidas/follow-ups explícitos

- #272 — contração física de aliases/colunas legadas em `corporate_events`;
- #149 — TWR dedicado de Tesouro Direto e Renda Fixa;
- #150 — histórico persistido do IBOV;
- #226 → #216 → #158 — cadeia obrigatória antes de dados reais;
- #246 + #57 — Metas + Análise de Carteira somente após estabilização;
- hardening mínimo de logs administrativos permanece backlog separado e não invalida o baseline funcional certificado.

## Promoção para `main`

PR estrutural aberta: #281 — `stable-15jun` → `main`.

A PR deve preservar `ready_for_real_data=false` e não deve incorporar automaticamente PRs Dependabot ou mudanças funcionais fora do escopo de estabilização.
