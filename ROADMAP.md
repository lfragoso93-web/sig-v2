# Roadmap modular — SGI v2

> Última atualização: 07/08/2026

## Direção atual

O SGI v2 está em **reorganização de governança e estabilização arquitetural** antes da próxima fase funcional.

A Issue #227 é o gate-mãe que impede dados reais antes da certificação. A Issue #247 é a executora do trabalho atual: primeiro reconciliar documentação, Issues e PRs; depois auditar legado, serviços, routers, endpoints e integrações.

A Issue #241 está concluída. Alembic ↔ MetaData convergiu para todos os domínios estabilizados. `goals` é a única exceção deliberada e pertence ao futuro macroprojeto #246 + #57; não deve receber migration apenas para silenciar `alembic check`.

## Estado por módulo

| Módulo | Estado atual | Próxima decisão |
|---|---|---|
| Core backend e autenticação | Estável | auditoria geral #247 |
| Carteiras e transações | Consolidado | auditoria de endpoints/serviços #247 |
| Dados canônicos / DB-first | Consolidado | preservar contratos únicos |
| B3 / Tesouro / benchmarks / câmbio | Consolidado | IBOV #150 e TWR #149 depois da auditoria |
| Proventos | Implementação canônica concluída | execução real bloqueada #226/#227 |
| Snapshots e valuation | Consolidado | TWR dedicado #149 |
| Resumo e Patrimônio | Consolidado | UX #90 é backlog |
| Rentabilidade | Consolidada | TWR #149 / IBOV #150 |
| IRPF | Canônico; validação real futura | manter bloqueado para dados reais |
| Eventos corporativos | Núcleo canônico consolidado | confirmar legado residual #129 durante #247 |
| Metas | Não estabilizado | redesenho conjunto #246 + #57 |
| Análise de Carteira | Não implementada funcionalmente | redesenho conjunto #246 + #57 |
| Convergência Alembic/ORM | Concluída fora de `goals` | manter gates |
| Pré-produção/rebuild | Bloqueada | retomar somente após certificação estrutural |
| IBOV persistido | Planejado | #150 |
| TWR Tesouro/Renda Fixa | Planejado | #149 |

Percentuais de progresso foram removidos deste roadmap porque geravam falsa precisão em módulos cuja pendência é arquitetural ou operacional.

## Qualidade estrutural registrada

Baseline no HEAD `17beeb9e6ae70f51d523e273bebda368872f81de`:

- Build Docker aprovado.
- `compileall` aprovado.
- 15 testes estruturais aprovados.
- `app.main` importado integralmente.
- Gates contra consumidores legados e deriva Alembic/ORM aprovados.

Commits posteriores de governança/documentação não alteram runtime ou banco.

## Ordem canônica de execução

### Fase 1 — Governança e documentação — AGORA

Issue executora: #247. Gate-mãe: #227.

- [ ] reconciliar README, ROADMAP, CHANGELOG, arquitetura e continuidade;
- [ ] revisar e classificar todas as Issues abertas;
- [ ] retirar status, sprints, dependências e próximos passos obsoletos;
- [ ] manter PRs Dependabot em fila técnica separada;
- [ ] garantir uma única ordem de execução em toda documentação viva.

### Fase 2 — Auditoria arquitetural pós-convergência

Issue executora: #247.

- [ ] revisar routers, services, models, integrações, jobs, CLIs, scheduler e entrypoint;
- [ ] revisar frontend: rotas, redirects, stubs e API clients;
- [ ] classificar endpoints/aliases de compatibilidade por consumidor comprovado;
- [ ] eliminar duplicação, legado e APIs redundantes em commits pequenos;
- [ ] confirmar pendências reais da #129;
- [ ] acionar #130/#127 somente quando achados concretos exigirem.

### Fase 3 — Performance e benchmarks

- [ ] #150 — histórico persistido do IBOV;
- [ ] #149 — TWR diário de Tesouro Direto e Renda Fixa;
- [ ] reconciliar snapshots de classe e consolidado.

### Fase 4 — Retomada operacional

Bloqueada pelas fases anteriores e pela #227.

- [ ] #226 — executar duas rodadas reais controladas de Proventos;
- [ ] #216 — reconciliar e fechar gate de seeds;
- [ ] #158 — retomar CSV, posições, snapshots e reconciliação financeira;
- [ ] somente após certificação, autorizar primeira carga real.

### Fase 5 — Metas + Análise de Carteira

Somente após estabilização e promoção da base:

- [ ] tratar #246 + #57 como um único macroprojeto;
- [ ] definir domínio antes de migration;
- [ ] decidir taxonomia de metas e fronteira com `portfolio_class_targets`;
- [ ] definir valores calculados versus persistidos;
- [ ] redesenhar schema, ORM, API e frontend de forma coerente.

## Classificação das Issues abertas

### Trabalho atual

- #227 — gate-mãe de estabilização.
- #247 — governança + auditoria pós-convergência.

### Bloqueadas / dependentes

- #129 — confirmar pendências reais durante #247.
- #150 — após #247.
- #149 — após #247.
- #226 — execução real bloqueada.
- #216 — depende de #226.
- #158 — depende de #216/#226 e certificação.
- #246 + #57 — bloqueadas até estabilização da base.

### Backlog / evolução não bloqueadora

- #58 — Janela Global do Ativo.
- #83 — Backup/Restore pela interface.
- #90 — refinamento UX de Patrimônio.
- #97 — Google OAuth.
- #127 — provedores configuráveis pelo Superadmin.
- #130 — evolução ampla BRAPI/enriquecimento, exceto itens necessários para achados da auditoria.

## PRs Dependabot

Fila técnica separada do roadmap funcional. Abertas em 07/08/2026:

- #236 — `undici` 7.29.0, com correções de segurança;
- #235 — `hadolint-action` 3.4.0;
- #234 — patches React;
- #231 — build-tools, incluindo TypeScript 7; risco maior e revisão obrigatória;
- #230 — FastAPI/Uvicorn;
- #223 — `@hookform/resolvers`.

Nenhuma deve ser incorporada automaticamente durante a reorganização. Cada PR exige avaliação de risco, CI e compatibilidade.

## Estado operacional

- Benchmarks e câmbio: seeds executados e reconciliados.
- Proventos: contrato `pre-prod-dividends-seed.v2` concluído, execução real pendente e bloqueada.
- Contração física de tabelas legadas de Proventos: preparada, não executada.
- CSV real, posições e snapshots: suspensos.
- Boot de sincronização de mercado: desabilitado por padrão.
- Rebuilds/seeds externos: opt-in.

## Gate para promoção estrutural

A próxima PR `stable-15jun` → `main` deve ser preparada apenas quando:

1. a Etapa 1 da #247 estiver documentalmente limpa;
2. a auditoria arquitetural da Etapa 2 estiver concluída;
3. achados críticos tiverem decisão explícita;
4. testes estruturais/runtime estiverem verdes;
5. documentação e Issues estiverem sincronizadas novamente.
