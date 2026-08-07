# Roadmap modular — SGI v2

> Última atualização: 07/08/2026

## Direção atual

O SGI v2 está em **auditoria arquitetural e preparação do bootstrap inicial** antes da próxima fase funcional.

A Issue #227 é o gate-mãe que impede dados reais antes da certificação. A Issue #247 executa a auditoria atual de legado, serviços, routers, endpoints e integrações.

A Issue #241 está concluída. Alembic ↔ MetaData convergiu para todos os domínios estabilizados. `goals` é a única exceção deliberada e pertence ao futuro macroprojeto #246 + #57.

## Regra operacional canônica

Antes de liberar criação/importação de carteiras reais, o sistema deve executar um bootstrap idempotente que carregue e persista todo o conjunto de dados necessário: catálogo, metadados, históricos, Proventos, eventos corporativos, Tesouro, benchmarks, câmbio e séries auxiliares.

Depois do bootstrap, consultas externas recorrentes ficam restritas a:

- preço intraday;
- preço oficial/de fechamento diário.

Demais módulos e requests funcionais devem operar exclusivamente sobre dados persistidos.

## Estado por módulo

| Módulo | Estado atual | Próxima decisão |
|---|---|---|
| Core backend e autenticação | Estável | auditoria geral #247 |
| Carteiras e transações | Consolidado | preservar CRUD sem sync externo |
| Dados canônicos / DB-first | Consolidado | fechar fronteira provider/bootstrap |
| B3 / Tesouro / benchmarks / câmbio | Persistidos | integrar ao bootstrap inicial |
| Proventos | Implementação canônica concluída | carregar no bootstrap e validar #226 |
| Snapshots e valuation | Consolidado | TWR dedicado #149 |
| Resumo e Patrimônio | Consolidado | manter DB-first |
| Rentabilidade | Consolidada | TWR #149 / IBOV #150 |
| IRPF | Canônico | validação real futura |
| Eventos corporativos | Núcleo canônico consolidado | bootstrap + auditoria residual #129 |
| Metas | Não estabilizado | redesenho conjunto #246 + #57 |
| Análise de Carteira | Não implementada funcionalmente | redesenho conjunto #246 + #57 |
| Convergência Alembic/ORM | Concluída fora de `goals` | manter gates |
| Bootstrap inicial | Arquitetura a consolidar | obrigatório antes de dados reais |
| Pré-produção/rebuild | Bloqueada | retomar somente após certificação |
| IBOV persistido | Planejado | #150 |
| TWR Tesouro/Renda Fixa | Planejado | #149 |

## Qualidade estrutural registrada

Checkpoint certificado no HEAD `08414af3a7b570ae9753e83ba5eecf2c17f20e42`:

- Build Docker aprovado.
- 7 testes do checkpoint de auditoria aprovados.
- `compileall` aprovado.
- `app.main` importado integralmente.
- Working tree limpa.

## Ordem canônica de execução

### Fase 1 — Auditoria arquitetural — AGORA

Issue executora: #247. Gate-mãe: #227.

- [ ] revisar routers, services, models, integrações, jobs, CLIs, scheduler e entrypoint;
- [ ] remover consultas externas de requests funcionais fora de preço intraday/fechamento;
- [ ] revisar frontend: rotas, redirects, stubs e API clients;
- [ ] classificar endpoints/aliases de compatibilidade por consumidor comprovado;
- [ ] eliminar duplicação, legado e APIs redundantes em commits pequenos;
- [ ] confirmar pendências reais da #129 e acionar #130/#127 somente quando necessário.

### Fase 2 — Bootstrap inicial e readiness

- [ ] consolidar um pipeline único, idempotente e auditável de bootstrap;
- [ ] carregar catálogo e metadados de ativos;
- [ ] carregar históricos de preços necessários;
- [ ] carregar Proventos e eventos corporativos globais;
- [ ] carregar Tesouro, benchmarks, câmbio e séries auxiliares;
- [ ] registrar estado/versionamento do bootstrap;
- [ ] impedir readiness para uso real enquanto o bootstrap não estiver certificado;
- [ ] manter runtime externo recorrente limitado a intraday e fechamento diário.

### Fase 3 — Performance e benchmarks

- [ ] #150 — histórico persistido do IBOV;
- [ ] #149 — TWR diário de Tesouro Direto e Renda Fixa;
- [ ] reconciliar snapshots de classe e consolidado.

### Fase 4 — Retomada operacional

Bloqueada pelas fases anteriores e pela #227.

- [ ] #226 — executar duas rodadas reais controladas de Proventos;
- [ ] #216 — reconciliar e fechar gate de seeds/bootstrap;
- [ ] #158 — retomar CSV, posições, snapshots e reconciliação financeira;
- [ ] somente depois liberar primeira carteira real.

### Fase 5 — Metas + Análise de Carteira

Somente após estabilização e promoção da base:

- [ ] tratar #246 + #57 como um único macroprojeto;
- [ ] definir domínio antes de migration;
- [ ] redesenhar schema, ORM, API e frontend de forma coerente.

## Classificação das Issues abertas

### Trabalho atual

- #227 — gate-mãe de estabilização e readiness.
- #247 — auditoria pós-convergência e consolidação da fronteira de providers.

### Bloqueadas / dependentes

- #129 — confirmar pendências reais durante #247.
- #150 — após #247/bootstrap.
- #149 — após #247/bootstrap.
- #226 — execução real bloqueada.
- #216 — gate de seeds/bootstrap.
- #158 — depende de #216/#226 e certificação.
- #246 + #57 — bloqueadas até estabilização da base.

### Backlog / evolução não bloqueadora

- #58 — Janela Global do Ativo.
- #83 — Backup/Restore pela interface.
- #90 — refinamento UX de Patrimônio.
- #97 — Google OAuth.
- #127/#130 — evolução ampla de provedores além do necessário para os achados da auditoria.

## Estado operacional

- CRUD de transações não inicia ingestão externa automática.
- GETs financeiros auditados permanecem DB-first.
- A arquitetura alvo exige bootstrap completo antes de criação/importação de carteiras reais.
- Após o bootstrap, somente preço intraday e fechamento diário podem consultar providers de forma recorrente.
- Rebuilds e correções históricas permanecem operações explícitas e controladas.
- Dados reais continuam bloqueados pela #227.

## Gate para promoção estrutural

A próxima PR `stable-15jun` → `main` deve ser preparada apenas quando:

1. a auditoria arquitetural da #247 estiver concluída;
2. a fronteira provider/bootstrap estiver formalizada e protegida por gates;
3. o desenho do bootstrap/readiness estiver coerente com #227/#216/#158;
4. achados críticos tiverem decisão explícita;
5. testes estruturais/runtime estiverem verdes;
6. documentação e Issues estiverem sincronizadas novamente.
