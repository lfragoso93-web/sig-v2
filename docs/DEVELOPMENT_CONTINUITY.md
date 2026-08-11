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
- #248 — bootstrap certificado, cobertura CRIPTO e fronteira única de providers.
- #249 — readiness explícito do bootstrap — **concluída**.
- #250 — orquestrador global do bootstrap e exceções de provider/lifecycle.
- #254 — integração estrutural de eventos corporativos ao bootstrap — wrapper, testes e integração v4 publicados; validação integrada ainda pendente.
- #265 — shallow histories CRIPTO — **concluída em 11/08/2026** com fila rasa zerada.
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

## Checkpoint CRIPTO — 11/08/2026

HEAD canônico de entrada da triagem BC/BD: `6a33c8edc811965c9eabeba210d489c2f822334d`.

A recuperação massiva de shallow histories terminou e não deve ser reaberta sem regressão concreta:

- total CRIPTO: 481 ativos;
- `HISTORY_START_EXHAUSTED = 369`;
- `HISTORY_START_COMPLEMENT_GAPPED = 87`;
- `HISTORY_START_SHALLOW_UNAVAILABLE = 14`;
- `HISTORY_START_SHALLOW_VERIFIED = 10`;
- `HISTORY_UNAVAILABLE = 1` (`XUSD`);
- `shallow_histories = 0`;
- duplicidades globais = 0;
- `blocking_seams = 88`.

Os 88 seams bloqueantes estão reconciliados como 87 ativos `HISTORY_START_COMPLEMENT_GAPPED` mais um seam adicional em `LA`, que permanece `HISTORY_START_SHALLOW_UNAVAILABLE` com gap conhecido de 23 dias.

A próxima fase não é de backfill massivo. BC/BD são auditorias DB-only/read-only:

- **BC** classifica nominalmente os 87 `HISTORY_START_COMPLEMENT_GAPPED` por tamanho do gap e expõe metadados persistidos de provider/costura, sem inferir causa sem evidência externa;
- **BD** inventaria os 14 `HISTORY_START_SHALLOW_UNAVAILABLE` e o único `HISTORY_UNAVAILABLE`, incluindo cobertura persistida, fontes, tentativas e último erro de provider;
- nenhum dos dois blocos chama provider, altera lifecycle, escreve preços ou relaxa readiness.

CLIs de auditoria:

- `python -m app.cli.pre_prod_crypto_gap_classification_audit`;
- `python -m app.cli.pre_prod_crypto_unavailable_history_audit`.

Somente após a execução local e a classificação nominal desses residuais deve ser discutido um contrato como `ready_with_known_exceptions`; não implementar essa mudança antes da evidência BC/BD.

## Estado certificado localmente anterior — 08/08/2026

Último checkpoint anterior certificado pelo usuário: `0e8d96c081a0e788a9edcf69901a134b29b7f696`.

Validação Docker:

- build do backend aprovado;
- suíte dirigida: **22 passed**;
- `python -m compileall -q app tests`: aprovado;
- import integral de `app.main`: aprovado;
- HEAD local igual ao esperado.

Esse checkpoint certificou o `system-bootstrap.v2` com contexto de identidade e etapa FX. Os trabalhos posteriores evoluíram até o bootstrap v4 e a certificação operacional do histórico CRIPTO descrita acima.

## Estado estrutural do bootstrap

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

1. Executar e certificar localmente BC: auditoria dos 87 `HISTORY_START_COMPLEMENT_GAPPED`.
2. Executar e certificar localmente BD: auditoria dos 14 `HISTORY_START_SHALLOW_UNAVAILABLE` + `XUSD`.
3. Classificar as causas reais somente a partir das evidências nominais BC/BD; não usar heurística por ticker.
4. Decidir, com evidência, se o readiness operacional deve distinguir `ready`, `ready_with_known_exceptions` e `blocked`.
5. Manter `ready_for_real_data=false` enquanto #248/#227 não certificarem o contrato final.
6. Continuar #247/#129 para achados residuais de routers/services/providers/aliases.
7. Retomar #226 → #216 → #158 somente depois da certificação estrutural e da autorização operacional apropriada.
8. Somente depois iniciar #246 + #57 (Metas + Análise).

## Prompt mínimo para nova conversa

```text
@GitHub Continue o SGI v2 seguindo `docs/DEVELOPMENT_CONTINUITY.md`.

Repo: lfragoso93-web/sig-v2
Branch: stable-15jun
Gate-mãe: #227
Bootstrap/readiness CRIPTO: #248
Orquestrador/exceções: #250
Shallow histories: #265 concluída

Checkpoint de entrada BC/BD:
6a33c8edc811965c9eabeba210d489c2f822334d

Estado CRIPTO:
- 481 ativos;
- 369 EXHAUSTED;
- 87 COMPLEMENT_GAPPED;
- 14 SHALLOW_UNAVAILABLE;
- 10 SHALLOW_VERIFIED;
- 1 HISTORY_UNAVAILABLE (XUSD);
- shallow_histories=0;
- duplicates=0;
- blocking_seams=88 (87 GAPPED + LA).

Próxima ação: executar BC/BD exclusivamente read-only, classificar evidências e somente depois discutir tratamento das exceções/readiness.
```