# Roadmap de desenvolvimento no lab OCI — 2026-08-25

Este plano organiza os próximos blocos de desenvolvimento do SGI v2 no ambiente de laboratório OCI, antes de qualquer promoção para produção.

## Premissas

- Branch de desenvolvimento: `stable-15jun`.
- `main` permanece intocável até validação explícita e merge posterior.
- Ambiente atual: laboratório OCI E2 Micro, acessado por Cloudflare Tunnel.
- Não usar recursos pagos OCI.
- Não habilitar UFW neste ciclo.
- Não publicar portas de backend/frontend; exposição apenas via tunnel.
- Não versionar `.env`, segredos, dumps, artefatos ou dados reais.
- `test_ready=true` permite dados fictícios/descartáveis.
- `ready_for_real_data=false` continua bloqueando dados reais, CSV real, snapshots de produção e seeds reais sem autorização formal.

## Estado verificado nesta retomada

- `scripts/oci_smoke_test.sh` passa no lab OCI.
- Backend, frontend, PostgreSQL, Redis e Cloudflared estão em execução.
- Compose OCI renderiza sem published ports.
- Backend sobe via `entrypoint.sh`, executando migrations e seed/superadmin antes do Uvicorn.
- GitHub CLI autenticado com acesso ao repositório.
- Code Scanning aberto: nenhum alerta encontrado na consulta atual.
- Dependabot alerts abertos: nenhum alerta encontrado na consulta atual.
- PRs abertas: 12.
- Issues abertas consideradas neste plano: 19.

## Prioridade por severidade, esforço e utilidade

| Ordem | Bloco | Issues/PRs | Severidade | Esforço | Utilidade | Decisão |
|---:|---|---|---|---|---|---|
| 1 | Fechar estabilização operacional OCI do lab | #284 | Alta | Médio | Alta | Continuar agora |
| 2 | Corrigir/registrar PRs com CI falhando | PR #279, PR #235 | Alta | Baixo/Médio | Alta | Antes de merge de dependências |
| 3 | Validar PRs Dependabot verdes em `stable-15jun` | PRs #286, #285, #280, #278, #277, #276, #275, #274, #273, #261 | Média | Médio | Alta | Em lotes pequenos |
| 4 | Revalidar gate de dados reais | #227, #226, #216, #158 | P0 | Médio | Máxima | Bloqueia seed completo real |
| 5 | Executar seed completo apenas em modo permitido | #216, #226, #158 | P0 | Alto | Máxima | Primeiro com dados fictícios/descartáveis; real só com autorização |
| 6 | Hardening operacional de backup/restore | #83 | Alta | Alto | Alta | Antes de alegar DR operacional |
| 7 | Central de Bootstrap SuperAdmin | #253 | Alta | Alto | Alta | Após gates básicos estabilizados |
| 8 | Histórico persistido do IBOV | #150 | Média | Médio | Alta | Após seed/rebuild validado |
| 9 | TWR diário Tesouro/Renda Fixa | #149 | Alta | Alto | Alta | Após séries e snapshots confiáveis |
| 10 | Contrair aliases físicos de `corporate_events` | #272 | Média | Alto | Média | Bloco arquitetural separado |
| 11 | Metas + Análise de Carteira | #246, #57 | Média | Muito alto | Alta | Macroprojeto posterior |

## Fase 0 — higiene imediata já iniciada

Objetivo: garantir que o laboratório sinalize corretamente falhas reais.

Concluído nesta sessão:

- preservar `entrypoint.sh` em overlays Compose;
- validar migrations/seed/superadmin no startup do backend;
- corrigir falso positivo do smoke test em logs mascarados do Cloudflared.

Critério de saída:

- `sh scripts/oci_smoke_test.sh` aprovado;
- `git status --short` limpo;
- commits pequenos na `stable-15jun`.

## Fase 1 — estabilização OCI do lab

Issue principal: #284.

Entregas:

1. Atualizar documentação OCI com o estado real do lab:
   - domínio público via Cloudflare Tunnel;
   - frontend apontado para `frontend:80`;
   - sem SSH no tunnel;
   - sem portas publicadas no host;
   - smoke test oficial aprovado.
2. Criar checklist de restart/reboot:
   - `docker compose ps`;
   - `/health`;
   - frontend público;
   - smoke OCI;
   - persistência de Postgres/Redis.
3. Confirmar limites Always Free:
   - uso de disco;
   - memória;
   - ausência de serviços pagos.

Critério de saída:

- lab reprodutível por runbook;
- sem dependência de configuração manual não documentada;
- nenhum segredo em documentação.

## Fase 2 — PRs abertas e CI

Objetivo: impedir que dependências atrasadas se misturem com features.

### PRs com falha

- PR #279 — build-tools frontend:
  - falha em `Frontend – lint, type check and build`;
  - falha em `Dependency audit – Node.js`;
  - tratar em branch/lote próprio e validar em `stable-15jun`.
- PR #235 — `hadolint/hadolint-action`:
  - falha em `Dockerfile lint – backend`;
  - investigar regra nova antes de aceitar upgrade.

### PRs verdes/mergeable

- PR #286 — `mypy`;
- PR #285 — `reportlab`;
- PR #280 — `lucide-react`;
- PR #278 — `recharts`;
- PR #277 — `fastapi-stack`;
- PR #276 — `zustand`;
- PR #275 — `sqlalchemy-stack`;
- PR #274 — `eslint-stack`;
- PR #273 — `react-stack`;
- PR #261 — `redis`.

Critério de validação por lote:

- aplicar sobre `stable-15jun`, nunca direto em `main`;
- backend: testes focados, `compileall`, import `app.main`, Alembic;
- frontend: lint, typecheck, testes e build;
- segurança: `pip-audit`, `npm audit`, Gitleaks/Trivy quando aplicável;
- smoke OCI após rebuild.

## Fase 3 — gate de dados reais

Issues: #227, #226, #216, #158.

Decisão vigente:

- dados fictícios/descartáveis são permitidos;
- dados reais continuam bloqueados;
- Proventos reais exigem autorização explícita da #226;
- `ready_for_real_data=true` não deve ser forçado manualmente.

Trabalho permitido agora no lab:

1. Ensaiar fluxo completo com dados descartáveis:
   - usuário lab;
   - carteira lab;
   - operações sintéticas;
   - rebuild de posições/snapshots se suportado por entrada segura;
   - validação de telas.
2. Auditar CLIs/wrappers de seed:
   - benchmarks macro;
   - câmbio;
   - Tesouro;
   - Proventos.
3. Confirmar quais comandos exigem rede externa e quais podem rodar offline.
4. Preparar checklist de autorização para execução real futura.

Trabalho bloqueado sem autorização:

- duas execuções reais de Proventos;
- CSV real completo;
- reconstrução/snapshots com dados reais;
- promoção formal para `ready_for_real_data=true`.

## Fase 4 — seed completo de teste

Objetivo: testar funcionamento sistêmico sem quebrar o gate de dados reais.

Plano conservador:

1. Criar conjunto de dados sintéticos mínimo:
   - usuário SuperAdmin/lab;
   - carteira;
   - ativos de classes principais;
   - compras/vendas;
   - renda fixa/Tesouro quando possível;
   - proventos sintéticos;
   - FX/preços sintéticos.
2. Rodar pipelines/rebuilds permitidos.
3. Validar:
   - login/cadastro;
   - criação/remoção de carteira;
   - importação ou inserção controlada;
   - patrimônio;
   - rentabilidade;
   - IRPF;
   - snapshots;
   - restart dos containers;
   - smoke OCI.
4. Registrar lacunas antes de qualquer dado real.

Critério de saída:

- fluxo principal validado no lab;
- bugs reproduzíveis viram commits pequenos;
- nenhuma evidência sensível versionada.

## Fase 5 — hardening operacional

Issue: #83.

Motivo para vir antes de produção: o sistema já tem backup/restore via UI, mas a própria issue classifica como parcialmente implementado.

Ordem sugerida:

1. corrigir endpoint de download;
2. exigir reautenticação/confirmação auditável para restore;
3. registrar backup/restore/delete no `AuditLog`;
4. persistir status de jobs;
5. TTL/limpeza automática;
6. testes HTTP, serviço e frontend;
7. certificar restore apenas em banco isolado descartável.

## Fase 6 — bootstrap administrável

Issue: #253.

Escopo recomendado:

- UI SuperAdmin para status global;
- estágios nomeados;
- execução seletiva quando autorizada;
- bloqueio explícito de gates como #226;
- polling de estado;
- nenhuma recriação de endpoints legados separados.

Este bloco deve vir depois do smoke OCI e da matriz de seeds para não cristalizar fluxos operacionais ainda instáveis.

## Fase 7 — melhorias financeiras pós-gate

Issues: #150 e #149.

Ordem recomendada:

1. #150 — IBOV persistido DB-first:
   - desbloqueia benchmarks no frontend;
   - esforço médio;
   - alto valor de validação.
2. #149 — TWR diário para Tesouro/Renda Fixa:
   - alto valor funcional;
   - esforço alto;
   - depende de séries/snapshots confiáveis.

## Fase 8 — dívidas arquiteturais e macroprojetos

Issues: #272, #246 e #57.

Regras:

- #272 deve ser bloco isolado de schema, com inventário antes de migration;
- #246 + #57 devem ser desenhadas juntas;
- não criar migration de `goals` apenas para satisfazer Alembic;
- não duplicar `summary.v2`, `rentabilidade.v2` ou snapshots canônicos.

## Próximo bloco recomendado

Executar a Fase 1:

1. atualizar documentação OCI com o estado real do tunnel/domínio;
2. documentar rotina de restart/reboot do lab;
3. confirmar health/smoke após documentação;
4. commitar o runbook atualizado.

Depois disso, iniciar a Fase 2 pelos PRs com falha (#279 e #235), porque eles podem esconder incompatibilidades que afetariam qualquer lote posterior.
