# Roadmap modular — SGI v2

> Última atualização: 11/08/2026

## Direção atual

O SGI v2 está em **auditoria arquitetural e certificação do bootstrap inicial** antes da próxima fase funcional.

A Issue #227 é o gate-mãe que impede dados reais antes da certificação. A Issue #247 executa a auditoria atual de legado, serviços, routers, endpoints e integrações. A #248 coordena bootstrap/providers/readiness, a #250 executa o orquestrador global e a #267 restringe CRIPTO ao universo Top 100 por capitalização.

A Issue #241 está concluída. Alembic ↔ MetaData convergiu para todos os domínios estabilizados. `goals` é a única exceção deliberada e pertence ao futuro macroprojeto #246 + #57.

## Regra operacional canônica

Antes de liberar criação/importação de carteiras reais, o sistema deve executar um bootstrap idempotente que carregue e persista todo o conjunto de dados necessário: catálogo, metadados, históricos, Proventos, eventos corporativos, Tesouro, benchmarks, câmbio e séries auxiliares.

Depois do bootstrap, consultas externas recorrentes ficam restritas a preço intraday e preço oficial/de fechamento diário. Demais módulos e requests funcionais devem operar exclusivamente sobre dados persistidos.

## Política CRIPTO Top 100

O catálogo bruto de criptomoedas deixou de representar o universo operacional do SGI.

Contrato #267:

- ranking canônico de relevância: CoinGecko `/coins/markets`, ordem por `market_cap`;
- limite: Top 100 por `market_cap_rank`;
- universo suportado: Top 100 CoinGecko ∩ símbolos disponíveis na BRAPI;
- CoinGecko participa somente da seleção de universo durante bootstrap; BRAPI continua sendo a integração de disponibilidade/preços do SGI;
- ativos persistidos fora do universo suportado são preservados, mas não devem bloquear readiness CRIPTO;
- seed, histórico inicial e readiness usam o mesmo contrato de universo.

A auditoria anterior sobre 481 CRIPTO permanece como evidência histórica, não como obrigação de suporte.

## Estado por módulo

| Módulo | Estado atual | Próxima decisão |
|---|---|---|
| Core backend e autenticação | Estável | auditoria geral #247 |
| Carteiras e transações | Consolidado | preservar CRUD sem sync externo |
| Dados canônicos / DB-first | Consolidado | concluir certificação bootstrap/providers |
| B3 / Tesouro / benchmarks / câmbio | Persistidos e integrados ao bootstrap | validar cobertura/certificação |
| CRIPTO | Universo Top 100 por market cap formalizado em #267 | validar ranking/interseção e readiness residual |
| Proventos | Contrato `pre-prod-dividends-seed.v2` registrado no `system-bootstrap.v4` sob gate #226 | validar integração; carga real continua bloqueada |
| Snapshots e valuation | Consolidado | TWR dedicado #149 |
| Resumo e Patrimônio | Consolidado | manter DB-first |
| Rentabilidade | Consolidada | TWR #149 / IBOV #150 |
| IRPF | Canônico | validação real futura |
| Eventos corporativos | Integrados estruturalmente ao `system-bootstrap.v4` | validar wrapper/gate e concluir auditoria residual #129/#254 |
| Metas | Não estabilizado | redesenho conjunto #246 + #57 |
| Análise de Carteira | Não implementada funcionalmente | redesenho conjunto #246 + #57 |
| Convergência Alembic/ORM | Concluída fora de `goals` | manter gates |
| Bootstrap inicial | `system-bootstrap.v4`; todos os domínios externos obrigatórios representados | validação integrada e certificação final |
| Pré-produção/rebuild | Bloqueada | retomar somente após certificação |
| IBOV persistido | Planejado | #150 |
| TWR Tesouro/Renda Fixa | Planejado | #149 |

## Evidência CRIPTO pré-Top 100

Checkpoint BC/BD certificado em `9772b8c2bdb9875d85abc4a72ed0bebea39c222e`:

- 481 ativos CRIPTO auditados;
- 369 `HISTORY_START_EXHAUSTED`;
- 87 `HISTORY_START_COMPLEMENT_GAPPED`;
- 14 `HISTORY_START_SHALLOW_UNAVAILABLE`;
- 10 `HISTORY_START_SHALLOW_VERIFIED`;
- 1 `HISTORY_UNAVAILABLE` (`XUSD`);
- zero duplicidades;
- 88 seams bloqueantes;
- 71/87 gaps acima de 365 dias.

O finding justificou a separação entre catálogo descoberto e universo suportado.

## Ordem canônica de execução

### Fase 1 — Auditoria arquitetural + bootstrap — AGORA

Issues executoras: #247/#248/#250/#267. Gate-mãe: #227.

- [x] definir política de universo CRIPTO Top 100 por capitalização;
- [x] separar ranking de relevância do catálogo BRAPI;
- [x] limitar seed CRIPTO ao universo suportado;
- [x] limitar histórico CRIPTO do bootstrap ao universo suportado;
- [x] limitar readiness CRIPTO ao universo suportado;
- [ ] validar localmente ranking, interseção, seed, histórico e readiness Top 100;
- [ ] executar auditoria nominal do universo suportado e inventariar findings residuais;
- [ ] revisar routers, services, models, integrações, jobs, CLIs, scheduler e entrypoint;
- [x] remover consultas externas já identificadas de requests funcionais fora de preço intraday/fechamento;
- [ ] revisar frontend: rotas, redirects, stubs e API clients;
- [ ] classificar endpoints/aliases de compatibilidade por consumidor comprovado;
- [ ] eliminar duplicação, legado e APIs redundantes em commits pequenos;

### Fase 2 — Bootstrap inicial e readiness

- [x] consolidar uma porta única, idempotente e auditável de bootstrap;
- [x] carregar catálogo e metadados de ativos;
- [x] carregar históricos de preços necessários;
- [x] carregar Tesouro, benchmarks e câmbio como etapas explícitas;
- [x] registrar Proventos globais como etapa explícita sob gate operacional #226;
- [x] incorporar eventos corporativos globais sob wrapper dedicado, gate explícito e advisory lock (#254);
- [x] registrar estado/versionamento do bootstrap (`system-bootstrap.v4`);
- [x] impedir readiness para uso real enquanto o bootstrap não estiver certificado;
- [x] manter runtime externo recorrente limitado a intraday e fechamento diário;
- [ ] validar localmente o `system-bootstrap.v4` e seus gates de Proventos/eventos;
- [ ] certificar cobertura e idempotência do bootstrap completo;
- [ ] somente após certificação permitir `ready_for_real_data=true`.

### Fase 3 — Performance e benchmarks

- [ ] #150 — histórico persistido do IBOV;
- [ ] #149 — TWR diário de Tesouro Direto e Renda Fixa;
- [ ] reconciliar snapshots de classe e consolidado.

### Fase 4 — Retomada operacional

Bloqueada pelas fases anteriores e pela #227.

- [ ] #226 — executar duas rodadas reais controladas de Proventos na janela autorizada;
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
- #248 — bootstrap certificado e fronteira única de providers.
- #250 — orquestrador global `system-bootstrap.v4`.
- #267 — universo CRIPTO Top 100 por capitalização.
- #254 — integração estrutural de eventos corporativos, pendente de validação integrada/documentação final.

### Bloqueadas / dependentes

- #129 — auditoria residual de eventos corporativos após integração ao bootstrap.
- #150 — após #247/bootstrap.
- #149 — após #247/bootstrap.
- #226 — execução real bloqueada; contrato reutilizado estruturalmente pelo bootstrap.
- #216 — gate de seeds/bootstrap.
- #158 — depende de #216/#226 e certificação.
- #246 + #57 — bloqueadas até estabilização da base.

## Estado operacional

- CRUD de transações não inicia ingestão externa automática.
- GETs financeiros auditados permanecem DB-first.
- `system-bootstrap.v4` contém catálogo, históricos, Tesouro, benchmarks, FX, Proventos e eventos corporativos.
- CRIPTO no bootstrap/readiness é limitado ao Top 100 de market cap disponível na BRAPI.
- Registros CRIPTO fora desse universo permanecem auditáveis sem bloquear readiness.
- Sem `SGI_BOOTSTRAP_ENABLE_DIVIDENDS=true`, Proventos falha fechado antes de consultar provider; a autorização real continua pertencendo à #226.
- Sem `SGI_BOOTSTRAP_ENABLE_CORPORATE_EVENTS=true`, eventos corporativos também falham antes de provider.
- Após o bootstrap certificado, somente preço intraday e fechamento diário podem consultar providers de forma recorrente.
- Rebuilds e correções históricas permanecem operações explícitas e controladas.
- Dados reais continuam bloqueados pela #227.

## Gate para promoção estrutural

A próxima PR `stable-15jun` → `main` deve ser preparada apenas quando:

1. a auditoria arquitetural da #247 estiver concluída;
2. a fronteira provider/bootstrap estiver formalizada e protegida por gates;
3. o bootstrap obrigatório estiver integralmente representado e validado;
4. o universo CRIPTO Top 100 estiver operacionalmente certificado;
5. o desenho do readiness estiver coerente com #227/#216/#158;
6. achados críticos tiverem decisão explícita;
7. testes estruturais/runtime estiverem verdes;
8. documentação e Issues estiverem sincronizadas novamente.
