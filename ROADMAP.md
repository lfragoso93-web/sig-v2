# Roadmap modular — SGI v2

> Última atualização: 04/09/2026

## Rebaseline pós-merge PR #302 — 01/09/2026

- PR #302 foi mergeada em `main` pelo commit `7861268a2528d80e8c23dfc55f7b0800402abc6d`.
- `stable-15jun` segue como branch de desenvolvimento em `2c9358629b3e5e9206a365ebeac45f9272dfd48e`.
- `main` está um commit à frente apenas pelo merge commit; não há divergência funcional pendente da #302.
- Próximos blocos continuam sem PR nova até fechamento de macrobloco validado.
- PRs abertas atuais: nenhuma após triagem e encerramento dos Dependabot #295, #296, #297, #298, #299, #300 e #301.

## Estado corrente — certificação funcional de carteira — 04/09/2026

- branch obrigatória de desenvolvimento: `stable-15jun`;
- baseline documental corrente antes deste bloco: `133ad9f5a72f6c8944eda58ce72da9ca5ce9238c`;
- #303 é o gate ativo da certificação funcional `PORTFOLIO-TEST-READY` com dados sintéticos/descartáveis;
- #306 foi concluída: o CRUD de Renda Fixa/Tesouro deixou de projetar estado paralelo em `fixed_income_investments`;
- #307 está em conclusão estrutural: model e consumers foram retirados e `20260903_drop_fixed_income` foi validada em bancos descartáveis, mas ainda não aplicada ao banco local principal;
- `transactions` é a fonte canônica do lifecycle financeiro de Renda Fixa e Tesouro Direto;
- no inventário pre-prod corrente, somente `transactions` e `corporate_events` são `export_before_cleanup`;
- #149 permanece aberta: Tesouro possui trilha TWR DB-first com fechamento diário exato; Renda Fixa permanece fail-closed enquanto não existir histórico diário dedicado;
- `ready_for_real_data=false` permanece obrigatório;
- desenvolvimento, migrations de validação e suítes pesadas ocorrem no ambiente local; OCI fica reservado à homologação do SHA exato já certificado localmente.

## Direção atual

O SGI v2 encerrou a fase principal de sanitização arquitetural e hardening de segurança. O foco atual é **certificação funcional e financeira de carteira sintética no ambiente local**, mantendo o OCI somente para homologação do SHA exato já certificado e sem liberar dados reais prematuramente.

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
| OCI lab | Homologação de SHA local certificado | não desenvolver nem executar suítes pesadas no host |
| Pré-produção/rebuild | Parcial | retomar após #226/#216 |
| IBOV persistido | Planejado | #150 após primeira certificação |
| TWR Tesouro/Renda Fixa | Em desenvolvimento | #149: Tesouro integrado a snapshots DB-first; Renda Fixa pendente |

## Ordem canônica de execução

### Fase 0 — baseline e segurança — CONCLUÍDA OPERACIONALMENTE

- [x] #247 — sanitização arquitetural concluída;
- [x] PR #281 — promoção estrutural;
- [x] bloco final da #269 implementado e promovido pela PR #282;
- [x] CI da PR #282 aprovado;
- [ ] manter `Security deep scan` e demais scanners como verificação recorrente; não presumir execução sem evidência.

### Fase 1 — certificação `PORTFOLIO-TEST-READY` — AGORA

1. concluir #307 e aplicar de forma controlada `20260903_drop_fixed_income` no banco local principal após os gates de backup e documentação;
2. certificar os casos financeiros sintéticos de Tesouro Direto e Renda Fixa sob #303/#149, preservando comportamento fail-closed;
3. executar a suíte integrada da carteira sintética e reconciliar transações, posições, snapshots, patrimônio e rentabilidade;
4. reconstruir/recriar o runtime no SHA final da certificação e executar smoke do SHA exato;
5. sincronizar documentação e Issues com a evidência final;
6. somente depois homologar no OCI o mesmo SHA já certificado localmente.

### Fase 2 — gate operacional para dados reais

- [ ] #227 — revalidar decisão de readiness;
- [ ] #226 — duas execuções reais controladas de Proventos, somente após autorização explícita;
- [ ] #216 — reconciliar e fechar gate agregado de seeds/bootstrap;
- [ ] #158 — retomar CSV, posições, snapshots e reconciliação financeira;
- [ ] produzir GO / NO-GO explícito para `ready_for_real_data=true`.

### Fase 3 — performance e benchmarks

- [x] #150 — histórico persistido do IBOV materializado via COTAHIST no fluxo B3 DB-first;
- [ ] #149 — TWR diario de Tesouro Direto e Renda Fixa: Tesouro integrado a snapshots DB-first; Renda Fixa exige historico dedicado sem fallback;
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

- #303 — certificação funcional da carteira sintética antes de dados reais.
- #307 — retirada estrutural de `fixed_income_investments`; falta aplicação controlada da migration no banco local principal.
- #227 — gate-mãe de readiness.
- #226 — execução real controlada de Proventos.
- #216 — gate agregado de seeds/bootstrap.
- #158 — rebuild pré-produção e reconciliação.
- #284 — OCI: atualizar tracker para refletir que o lab já está operacional e separar lab de produção A1.

### P1 — após primeira certificação

- #150 — histórico persistido do IBOV: implementação DB-first via COTAHIST concluída em `stable-15jun`, pendente apenas de validação operacional real quando gates permitirem.
- #149 — TWR Tesouro/Renda Fixa: Tesouro integrado ao rebuild de snapshots quando houver fechamento diario exato persistido; Renda Fixa segue pendente por depender de historico dedicado sem fallback.

### P2 — dívida estrutural/operacional

- #272 — contração física de `corporate_events`.
- #83 — Backup/Restore administrativo.

### P3/P4 — backlog e produto

- #253, #58, #90, #97, #127 e #130.

### Bloqueadas / futuras

- #246 + #57 — Metas + Análise.

## PRs abertas

Em 01/09/2026, as 7 PRs Dependabot abertas contra `main` (#295, #296, #297, #298, #299, #300 e #301) foram triadas e encerradas.

#295, #296, #297, #298, #300 e #301 foram absorvidas integralmente em `stable-15jun`. #299 foi encerrada no formato original porque TypeScript 7 permanece incompatível com o peer range vigente de `typescript-eslint`; apenas `@vitejs/plugin-react 6.1.1` foi absorvido.

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
