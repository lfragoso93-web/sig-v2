# Continuidade de desenvolvimento — SGI v2

> Documento obrigatório para iniciar ou retomar qualquer conversa de desenvolvimento.

## Contexto permanente

- Repositório: `lfragoso93-web/sig-v2`.
- Branch obrigatória: `stable-15jun`.
- Nunca desenvolver diretamente na `main`.
- Dividir macroblocos em commits pequenos e rastreáveis.
- Ao final de cada bloco informar resumo técnico, impacto arquitetural, testes, SHA completo e próximo bloco.
- README, ROADMAP, CHANGELOG e documentação arquitetural devem refletir o estado real.
- `goals` permanece fora da estabilização corrente e não deve receber migration apenas para limpar Alembic.

## Gate e Issues vigentes

- #227 — gate-mãe antes de dados reais.
- #247 — auditoria pós-convergência.
- #248 — bootstrap certificado e fronteira única de providers.
- #249 — readiness explícito do bootstrap — **concluída**.
- #250 — orquestrador global do bootstrap — `system-bootstrap.v4`, ainda aberto até validação/certificação integral.
- #254 — integração estrutural de eventos corporativos ao bootstrap — wrapper, testes e integração v4 publicados; validação integrada ainda pendente.
- #226 — Proventos: contrato reutilizado pelo bootstrap, mas execução real continua bloqueada.
- #129 — eventos corporativos: núcleo consolidado; permanece aberta para auditoria residual de consumidores/aliases/provider boundaries.

## Regra canônica de providers

Política detalhada: `docs/PROVIDER_ACCESS_POLICY_2026-08.md`.

Antes da primeira carteira real, o banco deve estar carregado e reconciliado por bootstrap certificado. Depois disso:

- requests funcionais e cálculos financeiros são DB-first;
- provider recorrente somente para preço intraday e fechamento diário;
- lacuna comprovada de preço em data específica pode consultar apenas a janela mínima necessária, persistir o resultado e então refazer leitura DB-first;
- `get_price_at_date()` permanece leitor puro;
- CRUD de usuário/transações não dispara onboarding, seed ou backfill externo;
- catálogo, metadados, Proventos, eventos, benchmarks e câmbio não são sincronizados por jobs recorrentes.

No bootstrap inicial, cada domínio busca a maior cobertura válida suportada por sua fonte canônica. Não existe uma data inicial global arbitrária compartilhada entre preços, FX, Proventos e eventos.

## Liveness, bootstrap e readiness

Esses conceitos são distintos:

1. `/health` indica que o processo e suas dependências básicas estão vivos e também expõe o estado do bootstrap.
2. `system-bootstrap.v4` executa as etapas integradas e produz relatório fail-fast por etapa.
3. Todos os domínios externos obrigatórios já estão representados estruturalmente, mas isso **não** libera dados reais enquanto #248/#227 não certificarem cobertura, idempotência e gates.
4. `/ready` retorna sucesso somente quando `ready_for_real_data=true`.

Estados do bootstrap em memória: `not_started`, `running`, `ready`, `failed`.

O campo `certified_for_real_data` permanece `false`. Portanto, mesmo um relatório verde parcial não é autorização de go-live.

## Estado certificado localmente — 08/08/2026

Último HEAD certificado pelo usuário: `0e8d96c081a0e788a9edcf69901a134b29b7f696`.

Validação Docker:

- build do backend aprovado;
- suíte dirigida: **22 passed**;
- `python -m compileall -q app tests`: aprovado;
- import integral de `app.main`: aprovado;
- HEAD local igual ao esperado.

Esse checkpoint certifica o `system-bootstrap.v2` com contexto de identidade e etapa FX.

## Estado implementado após esse checkpoint — pendente de validação local integrada

### #248/#250 — Proventos no `system-bootstrap.v3`

- criado `system_bootstrap_dividends_stage.py`;
- reutiliza `pre-prod-dividends-seed.v2` e seus adapters estritos BRAPI/Yahoo;
- janela máxima local do estágio começa em `1970-01-01`, coerente com o limite técnico do histórico Yahoo usado pelo adapter;
- sem `SGI_BOOTSTRAP_ENABLE_DIVIDENDS=true`, o estágio falha antes de consultar provider;
- o opt-in técnico não substitui autorização operacional da #226;
- escrita permanece exclusivamente em `asset_dividends`;
- nenhum direito por carteira é materializado;
- `system_bootstrap_service.py` passou a `system-bootstrap.v3` e registra `asset_dividends` após `fx_rates`;
- o orquestrador continua fail-fast e `ready_for_real_data=false`.

Commits do bloco:

- `f3b2259c51fff0db398cd0315f63ec479c7f4c22` — wrapper/gate de Proventos;
- `0d45ef8fc9cf1107252631face5d1155d3c7a35c` — testes do gate;
- `89893af623a6837fb0ff2b0481d7d4ad1ec3261a` — registro no bootstrap v3;
- `ab13e0739a3b0ce5360b54f3b2deac07b543b6e4` — gate estrutural do contrato.

### #254/#248/#250 — eventos corporativos no `system-bootstrap.v4`

- criado `system_bootstrap_corporate_events_stage.py`;
- gate `SGI_BOOTSTRAP_ENABLE_CORPORATE_EVENTS` ocorre antes de sessão/provider;
- ativos elegíveis são lidos do banco e limitados a `ACAO`, `BDR` e `ETF_NACIONAL`;
- estágio usa `pg_advisory_xact_lock` e uma transação única;
- persistência passa exclusivamente por `sync_corporate_events_for_asset`;
- sucesso executa commit único; qualquer falha provoca rollback e interrompe os ativos seguintes;
- `asset_market_pipeline_service` e `dividend_backfill_service` não são usados;
- testes dirigidos cobrem gate, ordem do lock, filtro, commit, rollback/stop e relatório determinístico;
- `system_bootstrap_service.py` passou a `system-bootstrap.v4` e registra `corporate_events` após `asset_dividends`;
- `certified_for_real_data` permanece `false`;
- nenhum provider real foi executado durante esses blocos.

Commits estruturais do bloco:

- `80d8448c489ba61a4de556870e2ba58983358549` — wrapper/gate transacional;
- `7951f0981a3b650e60b94159e86ed709ad00ef22` — testes do estágio;
- `26b7db7f8d3d37ec5e47d1baf2415734e45b5332` — integração no bootstrap v4;
- `79fa4a4d929e24ced70ad86d04049082a0d52d89` — contrato estrutural atualizado.

### #248/#250 — FX certificado no checkpoint anterior

- contexto único de execução com `run_id`, branch e SHA completo;
- `POST /api/v1/admin/bootstrap` exige SHA completo;
- startup pode usar `SGI_BOOTSTRAP_COMMIT_SHA`;
- `system_bootstrap_fx_stage.py` reutiliza o seed PTAX transacional da #217;
- cobertura USD-BRL começa em `1994-07-01` por regra local do domínio;
- nenhuma data inicial global é imposta aos demais domínios.

### #249 — readiness explícito

- serviço `system_readiness_service.py` com estado em memória;
- separação entre `bootstrap_complete` e `ready_for_real_data`;
- bootstrap parcial nunca certifica dados reais;
- `/health` preserva função de liveness e inclui snapshot do bootstrap;
- `/ready` retorna 503 enquanto a certificação operacional estiver incompleta;
- Issue #249 encerrada após validação local.

## Scheduler

O scheduler recorrente está limitado a:

- preço intraday;
- fechamento diário de preços, restrito à data corrente;
- fechamento diário do Tesouro;
- manutenção local de snapshots/TWR.

Não agenda catálogo, benchmarks, Proventos, eventos, logos ou backfill histórico amplo.

## Ordem objetiva dos próximos blocos

1. Validar localmente `system-bootstrap.v4`, `system_bootstrap_dividends_stage.py`, `system_bootstrap_corporate_events_stage.py` e os gates relacionados, sem executar providers reais.
2. Reconciliar cobertura final/idempotência dos domínios obrigatórios da #248/#250/#254.
3. Manter `ready_for_real_data=false` até certificação integral.
4. Concluir #247/#129 para achados residuais de routers/services/providers/aliases.
5. Avaliar fechamento da #254 quando validação integrada e documentação estiverem completas.
6. Retomar #226 → #216 → #158 somente depois da certificação estrutural e da autorização operacional apropriada.
7. Somente depois iniciar #246 + #57 (Metas + Análise).

## Prompt mínimo para nova conversa

```text
@GitHub Continue o SGI v2 seguindo `docs/DEVELOPMENT_CONTINUITY.md`.

Repo: lfragoso93-web/sig-v2
Branch: stable-15jun
Gate-mãe: #227
Auditoria: #247
Bootstrap/providers: #248
Orquestrador: #250
Eventos no bootstrap: #254
Proventos: #226
Eventos corporativos residuais: #129

Último checkpoint certificado pelo usuário:
0e8d96c081a0e788a9edcf69901a134b29b7f696

Estado posterior pendente de validação integrada:
- system-bootstrap.v4;
- FX integrado;
- Proventos registrado sob gate SGI_BOOTSTRAP_ENABLE_DIVIDENDS;
- eventos corporativos registrados sob gate SGI_BOOTSTRAP_ENABLE_CORPORATE_EVENTS;
- ready_for_real_data continua false;
- nenhum provider real foi executado durante os blocos estruturais de eventos.

Preserve a regra:
- bootstrap completo e histórico máximo válido por domínio antes de dados reais;
- runtime externo apenas intraday/fechamento;
- exceção somente para lacuna de preço em data específica, com janela mínima e persistência antes do uso;
- catálogo e demais módulos DB-first;
- nenhuma execução real de Proventos sem gate/autorização da #226;
- não tocar em `goals` antes de #246/#57.
```