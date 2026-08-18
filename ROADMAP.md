# Roadmap modular — SGI v2

> Última atualização: 18/08/2026

## Direção atual

O SGI v2 concluiu a sanitização arquitetural da #247 e promoveu esse baseline para `main` pela PR #281. A revisão de segurança recebeu bloco final adicional pela PR #282.

A Issue #227 permanece como gate-mãe para dados reais.

- `test_ready=true`: uso controlado com dados fictícios/descartáveis continua permitido.
- `ready_for_real_data=false`: dados reais permanecem bloqueados até conclusão explícita dos gates operacionais.

Baseline atual:

- `stable-15jun`: `f36f02a32fcaf9345f98bb40f9065df7a2488101` antes da sincronização documental desta retomada;
- `main`: `b45dc435b8f20b218ff1dfbdd9ab1c868817ff3f`;
- conteúdo funcional pós-#282 equivalente entre as branches; a diferença era somente o merge commit em `main`.

A Issue #241 está concluída. Alembic ↔ MetaData convergiu para todos os domínios estabilizados. `goals` continua sendo a única exceção deliberada e pertence ao futuro macroprojeto #246 + #57.

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
| Core backend e autenticação | `test_ready` | preservar baseline e validar ambiente real |
| Carteiras e transações | Consolidado | preservar CRUD sem sync externo |
| Dados canônicos / DB-first | Consolidado | validar certificação operacional |
| B3 / Tesouro / benchmarks / câmbio | Persistidos e integrados ao bootstrap | validar cobertura no teste controlado |
| CRIPTO | #267 concluída | preservar contrato fail-closed |
| Proventos | `pre-prod-dividends-seed.v2` sob gate #226 | revalidar autorização antes de execução real |
| Snapshots e valuation | Consolidado | TWR dedicado #149 após gate real |
| Resumo e Patrimônio | Consolidado | manter DB-first |
| Rentabilidade | Consolidada | #150 / #149 após teste real |
| IRPF | Canônico | validação real futura controlada |
| Eventos corporativos | Integrados ao `system-bootstrap.v4` | preservar; dívida física isolada em #272 |
| Metas | Não estabilizado | redesenho conjunto #246 + #57 |
| Análise de Carteira | Não implementada funcionalmente | redesenho conjunto #246 + #57 |
| Convergência Alembic/ORM | Concluída fora de `goals` | manter gates |
| Bootstrap inicial | `system-bootstrap.v4` | auditar blockers para teste real |
| Pré-produção/rebuild | Bloqueada | retomar somente após gates autorizarem |
| IBOV persistido | Planejado | #150 após teste real |
| TWR Tesouro/Renda Fixa | Planejado | #149 após #150 conforme revalidação |

## Ordem canônica de execução

### Fase 0 — baseline e segurança — CONCLUÍDA OPERACIONALMENTE

- [x] #247 — sanitização arquitetural concluída;
- [x] PR #281 — promoção estrutural;
- [x] bloco final da #269 implementado e promovido pela PR #282;
- [x] CI da PR #282 aprovado;
- [ ] manter `Security deep scan` e demais scanners como verificação recorrente; não presumir execução sem evidência.

### Fase 1 — Gate para TESTE REAL controlado — AGORA

1. revalidar #227, #226, #216 e #158;
2. identificar blockers formais de dados reais;
3. não forçar `ready_for_real_data=true`;
4. não contornar autorização da #226;
5. resolver blockers em microblocos independentes;
6. quando autorizado, executar teste real auditável cobrindo infraestrutura, bootstrap, dados, reconciliação, persistência e segurança;
7. produzir decisão GO / NO-GO.

### Fase 2 — Performance e benchmarks

- [ ] #150 — histórico persistido do IBOV;
- [ ] #149 — TWR diário de Tesouro Direto e Renda Fixa;
- [ ] reconciliar snapshots de classe e consolidado.

### Fase 3 — Cadeia operacional para dados reais

- [ ] #226 — duas execuções reais controladas de Proventos, se ainda exigidas após auditoria;
- [ ] #216 — reconciliar e fechar gate de seeds/bootstrap;
- [ ] #158 — retomar CSV, posições, snapshots e reconciliação financeira;
- [ ] decidir formalmente `ready_for_real_data=true` somente depois dos gates.

### Fase 4 — Dívidas estruturais separadas

- [ ] #272 — contração física dos aliases/colunas legadas de `corporate_events`;
- [ ] demais dívidas estruturais válidas após auditoria.

### Fase 5 — Metas + Análise de Carteira

- [ ] tratar #246 + #57 como macroprojeto único;
- [ ] definir domínio e contratos antes de migration;
- [ ] somente depois redesenhar schema, ORM, API e frontend.

## Classificação das Issues abertas

### Trabalho atual

- #227 — gate-mãe de readiness e teste real.
- #226 — autorização/execução real controlada de Proventos.
- #216 — gate agregado de seeds/bootstrap.
- #158 — rebuild pré-produção e reconciliação.

### Próxima fase técnica

- #150 — histórico persistido do IBOV.
- #149 — TWR Tesouro/Renda Fixa.

### Dívida estrutural isolada

- #272 — contração física de `corporate_events`.

### Bloqueadas / futuras

- #246 + #57 — Metas + Análise.

### Backlog não bloqueador

- #253 — Central de Bootstrap SuperAdmin.
- #58 — Janela Global do Ativo.
- #83 — Backup/Restore hardening.
- #90 — UX de Patrimônio.
- #97 — Google OAuth.
- #127 — provedores configuráveis, sujeito à política fail-closed.
- #130 — evolução BRAPI, somente para lacunas concretas.

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

A próxima PR `stable-15jun` → `main` deve ser preparada apenas quando um novo macrobloco estiver concluído, validado e documentado. Não abrir PR a cada microcommit.
