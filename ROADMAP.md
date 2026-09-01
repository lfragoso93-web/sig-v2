# Roadmap modular — SGI v2

> Última atualização: 27/08/2026

## Direção atual

O SGI v2 encerrou a fase principal de sanitização arquitetural e hardening de segurança. O foco atual é **certificação operacional para testes integrados**, usando o ambiente OCI de laboratório sem liberar dados reais prematuramente.

A Issue #227 permanece como gate-mãe para dados reais.

- `test_ready=true`: uso controlado com dados fictícios/descartáveis continua permitido.
- `ready_for_real_data=false`: dados reais permanecem bloqueados até conclusão explícita dos gates operacionais.

Baseline no início deste rebaseline:

- `stable-15jun`: `a889edb6bbbb78feb7787c21b3439a0b835b73c6`;
- `main`: `3eeca232a8627f4562544739112d1dde82b879fb`;
- a PR #292 já foi promovida para `main`; `stable-15jun` avançou depois dela com pequenos blocos de documentação e hardening de smoke.

## Estado OCI de laboratório

O OCI deixou de ser apenas planejamento. Já existem evidências operacionais de laboratório:

- stack ARM64 validada para Ampere A1;
- E2 Micro descartável usado como lab enquanto A1 não estava disponível;
- Docker/Compose e baseline do host validados;
- Cloudflare Tunnel usado como única entrada pública web, sem expor backend, PostgreSQL ou Redis;
- frontend production build aprovado;
- hostname público validado com HTTP/2 200;
- smoke OCI aprovado;
- contratos de seed/bootstrap executados sem seeds reais:
  - FX/Macro/Tesouro: 81 aprovados, 1 ignorado;
  - B3/Asset Bootstrap/System Bootstrap: 70 aprovados;
  - Proventos: 93 aprovados, 8 ignorados;
- PR #291 publicou wrapper repetível de validação de contratos;
- PR #292 endureceu o smoke HTTP descartável;
- SHA `a889edb6bbbb78feb7787c21b3439a0b835b73c6` adicionou a prova de `403` para usuário comum em `/api/v1/admin/bootstrap/status`.

Essas evidências não alteram `ready_for_real_data=false`.

## Regra operacional canônica

Antes de liberar criação/importação de carteiras reais, o sistema deve executar um bootstrap idempotente que carregue e persista todo o conjunto de dados necessário: catálogo, metadados, históricos, Proventos, eventos corporativos, Tesouro, benchmarks, câmbio e séries auxiliares.

Depois do bootstrap, consultas externas recorrentes ficam restritas a preço intraday e preço oficial/de fechamento diário. Demais módulos e requests funcionais devem operar exclusivamente sobre dados persistidos.

## Política CRIPTO Top 100

O catálogo bruto de criptomoedas não representa o universo operacional do SGI.

Contrato #267:

- ranking canônico de relevância: CoinGecko `/coins/markets`, ordem por `market_cap`;
- limite: Top 100 por `market_cap_rank`;
- universo suportado: Top 100 CoinGecko ∩ símbolos disponíveis no catálogo do provedor de mercado integrado;
- CoinGecko participa somente da seleção de universo durante bootstrap;
- ativos persistidos fora do universo suportado são preservados, mas não bloqueiam readiness CRIPTO;
- seed, histórico inicial e readiness usam o mesmo contrato de universo.

## Estado por módulo

| Módulo | Estado atual | Próxima decisão |
|---|---|---|
| Core backend e autenticação | `test_ready` | certificar no lab e preservar baseline |
| Carteiras e transações | Consolidado | testar ponta a ponta com dados descartáveis |
| Dados canônicos / DB-first | Consolidado | validar certificação operacional |
| B3 / Tesouro / benchmarks / câmbio | Persistidos e integrados ao bootstrap | validar cobertura e restart |
| CRIPTO | #267 concluída | preservar contrato fail-closed |
| Proventos | `pre-prod-dividends-seed.v2` sob gate #226 | executar real somente após autorização |
| Snapshots e valuation | Consolidado | reconciliar no teste controlado |
| Resumo e Patrimônio | Consolidado | validar ponta a ponta |
| Rentabilidade | Consolidada | validar; #150/#149 depois do gate |
| IRPF | Canônico | validar com carteira controlada |
| Eventos corporativos | Integrados ao `system-bootstrap.v4` | preservar; dívida física em #272 |
| Metas | Não estabilizado | redesenho conjunto #246 + #57 |
| Análise de Carteira | Não implementada funcionalmente | redesenho conjunto #246 + #57 |
| Convergência Alembic/ORM | Concluída fora de `goals` | manter gate |
| Bootstrap inicial | `system-bootstrap.v4` | certificar contratos e operação |
| OCI lab | Operacional para testes descartáveis | executar bateria formal |
| Pré-produção/rebuild | Parcial | retomar após #226/#216 |
| IBOV persistido | Planejado | #150 após primeira certificação |
| TWR Tesouro/Renda Fixa | Planejado | #149 após primeira certificação |

## Ordem canônica de execução

### Fase 0 — baseline e segurança — CONCLUÍDA OPERACIONALMENTE

- [x] #247 — sanitização arquitetural concluída;
- [x] PR #281 — promoção estrutural;
- [x] bloco final da #269 implementado e promovido pela PR #282;
- [x] CI da PR #282 aprovado;
- [ ] manter `Security deep scan` e demais scanners como verificação recorrente; não presumir execução sem evidência.

### Fase 1 — rebaseline e certificação de TESTE — AGORA

1. sincronizar README, ROADMAP, CHANGELOG, `DEVELOPMENT_CONTINUITY` e Issues centrais com o estado OCI real;
2. executar qualidade completa no lab: backend, frontend, segurança e smoke;
3. validar restart, persistência, volumes, migrations e Redis fail-open;
4. validar `system-bootstrap.v4` e contratos sem executar seeds reais proibidos;
5. confirmar controles SuperAdmin e estados de readiness;
6. registrar achados em microblocos e corrigir blockers sem introduzir features.

### Fase 2 — gate operacional para dados reais

- [ ] #227 — revalidar decisão de readiness;
- [ ] #226 — duas execuções reais controladas de Proventos, somente após autorização explícita;
- [ ] #216 — reconciliar e fechar gate agregado de seeds/bootstrap;
- [ ] #158 — retomar CSV, posições, snapshots e reconciliação financeira;
- [ ] produzir GO / NO-GO explícito para `ready_for_real_data=true`.

### Fase 3 — performance e benchmarks

- [ ] #150 — histórico persistido do IBOV;
- [ ] #149 — TWR diário de Tesouro Direto e Renda Fixa;
- [ ] reconciliar snapshots de classe e consolidado.

### Fase 4 — dívidas estruturais separadas

- [ ] #272 — contração física dos aliases/colunas legadas de `corporate_events`;
- [ ] #83 — hardening residual de Backup/Restore administrativo;
- [ ] demais dívidas estruturais válidas após auditoria.

### Fase 5 — evolução de produto

- [ ] #253 — Central de Bootstrap SuperAdmin, se continuar necessária após certificação;
- [ ] #58 — Janela Global do Ativo;
- [ ] #90 — refinamento de UX de Patrimônio;
- [ ] #97 — Google OAuth;
- [ ] #130 — evolução BRAPI em blocos concretos, não como pacote monolítico.

### Fase 6 — Metas + Análise de Carteira

- [ ] tratar #246 + #57 como macroprojeto único;
- [ ] definir domínio e contratos antes de migration;
- [ ] somente depois redesenhar schema, ORM, API e frontend.

## Classificação das Issues abertas

### P0 — trabalho corrente / gate

- #227 — gate-mãe de readiness.
- #226 — execução real controlada de Proventos.
- #216 — gate agregado de seeds/bootstrap.
- #158 — rebuild pré-produção e reconciliação.
- #284 — OCI: atualizar tracker para refletir que o lab já está operacional e separar lab de produção A1.

### P1 — após primeira certificação

- #150 — histórico persistido do IBOV.
- #149 — TWR Tesouro/Renda Fixa.

### P2 — dívida estrutural/operacional

- #272 — contração física de `corporate_events`.
- #83 — Backup/Restore administrativo.

### P3/P4 — backlog e produto

- #253, #58, #90, #97, #127 e #130.

### Bloqueadas / futuras

- #246 + #57 — Metas + Análise.

## PRs abertas

No início deste rebaseline existe somente a PR Dependabot #289, TypeScript `6.0.3 -> 7.0.2`.

Ela não deve ser mergeada agora: `typescript-eslint 8.67.0` exige TypeScript `<6.1.0`, e a própria validação da PR #290 registrou falha de resolução do `npm` para esse upgrade. Tratar como bloqueada por compatibilidade do ecossistema.

## Estado operacional

- CRUD de transações não inicia ingestão externa automática.
- GETs financeiros auditados permanecem DB-first.
- `system-bootstrap.v4` contém catálogo, históricos, Tesouro, benchmarks, FX, Proventos e eventos corporativos.
- CRIPTO no bootstrap/readiness é limitado ao universo suportado Top 100.
- Sem `SGI_BOOTSTRAP_ENABLE_DIVIDENDS=true`, Proventos falha fechado antes de provider; a autorização real continua pertencendo à #226.
- Sem `SGI_BOOTSTRAP_ENABLE_CORPORATE_EVENTS=true`, eventos corporativos também falham antes de provider.
- Após bootstrap certificado, somente preço intraday e fechamento diário podem consultar providers de forma recorrente.
- Dados reais continuam bloqueados pela #227.
- Dados fictícios/descartáveis permanecem liberados sob `test_ready=true`.

## Gate para próxima promoção estrutural

A próxima PR `stable-15jun` → `main` deve ser preparada apenas quando este macrobloco de rebaseline/certificação estiver concluído, validado e documentado. Não abrir PR a cada microcommit.
