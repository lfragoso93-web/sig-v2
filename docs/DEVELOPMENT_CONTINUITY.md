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

BC/BD foram certificados localmente no HEAD `9772b8c2bdb9875d85abc4a72ed0bebea39c222e`.

Validação local:

- build Docker aprovado;
- testes dirigidos BC/BD: **2 passed**;
- `python -m compileall -q app tests`: aprovado;
- import integral de `app.main`: aprovado;
- `git diff --check`: aprovado;
- working tree limpa;
- duplicidades globais em `(asset_id, timestamp)`: 0.

Distribuição do lifecycle CRIPTO:

- total: 481 ativos;
- `HISTORY_START_EXHAUSTED = 369`;
- `HISTORY_START_COMPLEMENT_GAPPED = 87`;
- `HISTORY_START_SHALLOW_UNAVAILABLE = 14`;
- `HISTORY_START_SHALLOW_VERIFIED = 10`;
- `HISTORY_UNAVAILABLE = 1` (`XUSD`);
- `shallow_histories = 0`;
- `blocking_seams = 88`.

Os 88 seams bloqueantes estão reconciliados como 87 ativos `HISTORY_START_COMPLEMENT_GAPPED` mais um seam adicional em `LA`, que permanece `HISTORY_START_SHALLOW_UNAVAILABLE` e possui gap de 23 dias.

### BC — classificação dos 87 `HISTORY_START_COMPLEMENT_GAPPED`

Auditoria DB-only/read-only certificada, sem chamadas a provider, writes ou alteração de lifecycle.

Distribuição por tamanho do gap:

- `<= 30 dias`: 2 (`GALA = 22`, `WLFI = 27`);
- `31–90 dias`: 1 (`MIRA = 74`);
- `91–365 dias`: 13;
- `>365 dias`: 71;
- `unknown`: 0.

O maior gap observado é `COMP`, com 1.667 dias. A predominância de gaps longos impede tratá-los genericamente como tolerância de costura; a causa continua `requires_external_evidence`.

### BD — indisponibilidades residuais

Auditoria DB-only/read-only certificada para 15 ativos:

- 14 `HISTORY_START_SHALLOW_UNAVAILABLE`;
- 1 `HISTORY_UNAVAILABLE` (`XUSD`);
- 13 dos 14 shallow indisponíveis possuem exatamente 1 linha em `2026-08-10`;
- `LA` possui 2 linhas (`2026-07-17` e `2026-08-10`);
- `XUSD` possui zero linhas persistidas.

CLIs certificadas:

- `python -m app.cli.pre_prod_crypto_gap_classification_audit`;
- `python -m app.cli.pre_prod_crypto_unavailable_history_audit`;
- `python -m app.cli.pre_prod_crypto_readiness_audit`.

## Decisão arquitetural após BC/BD

BC e BD estão concluídos como auditorias read-only. Eles **não** autorizam:

- mudar lifecycle;
- marcar exceções permanentes;
- converter gaps em estado tolerado por heurística;
- promover `ready_for_real_data`;
- abrir uma nova PR estrutural para `main` apenas com base nesses números.

A próxima fase deve buscar evidência externa exclusivamente para classificar causa dos residuais. Prioridade recomendada:

1. investigar os casos curtos (`GALA`, `WLFI`, `MIRA`) porque permitem distinguir mais rapidamente atraso de fonte, symbol mapping ou evento de listagem/migração;
2. investigar os 15 casos BD (`14 SHALLOW_UNAVAILABLE + XUSD`), incluindo aliases/símbolos do provider;
3. amostrar grupos de gaps >365 dias por padrão de primeira data BRAPI/última data de complemento antes de qualquer tentativa massiva;
4. somente depois discutir contrato de readiness como `ready_with_known_exceptions`.

## Estado certificado localmente anterior — 08/08/2026

Checkpoint anterior certificado pelo usuário: `0e8d96c081a0e788a9edcf69901a134b29b7f696`.

- build do backend aprovado;
- suíte dirigida: **22 passed**;
- `compileall`: aprovado;
- import integral de `app.main`: aprovado.

Esse checkpoint certificou o `system-bootstrap.v2` com contexto de identidade e etapa FX. Os trabalhos posteriores evoluíram até o bootstrap v4 e a certificação operacional do histórico CRIPTO descrita acima.

## Estado estrutural do bootstrap

### #248/#250 — Proventos no `system-bootstrap.v3`

- `system_bootstrap_dividends_stage.py` reutiliza `pre-prod-dividends-seed.v2` e adapters estritos BRAPI/Yahoo;
- sem `SGI_BOOTSTRAP_ENABLE_DIVIDENDS=true`, o estágio falha antes de provider;
- o opt-in técnico não substitui autorização operacional da #226;
- escrita permanece exclusivamente em `asset_dividends`;
- nenhum direito por carteira é materializado;
- o orquestrador continua fail-fast e `ready_for_real_data=false`.

### #254/#248/#250 — eventos corporativos no `system-bootstrap.v4`

- `system_bootstrap_corporate_events_stage.py` usa gate antes de sessão/provider;
- lê ativos elegíveis do banco (`ACAO`, `BDR`, `ETF_NACIONAL`);
- usa advisory lock transacional;
- persistência passa exclusivamente por `sync_corporate_events_for_asset`;
- sucesso usa commit único e falha provoca rollback;
- `asset_market_pipeline_service` e `dividend_backfill_service` não participam;
- `certified_for_real_data` permanece `false`.

### #249 — readiness explícito

- `system_readiness_service.py` separa `bootstrap_complete` de `ready_for_real_data`;
- bootstrap parcial nunca certifica dados reais;
- `/health` mantém função de liveness;
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

1. Abrir/iniciar investigação read-only de causa dos residuais BC/BD, priorizando `GALA`, `WLFI`, `MIRA` e os 15 indisponíveis.
2. Verificar aliases, símbolos atuais/históricos e limites reais dos providers antes de qualquer write.
3. Amostrar os gaps longos para identificar clusters de causa e evitar 71 investigações idênticas caso exista um padrão comum.
4. Somente com evidência, propor lifecycle/exceções e decidir se o readiness operacional deve distinguir `ready`, `ready_with_known_exceptions` e `blocked`.
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

Último checkpoint BC/BD certificado:
9772b8c2bdb9875d85abc4a72ed0bebea39c222e

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

BC certificado:
- <=30d: 2 (GALA 22, WLFI 27);
- 31-90d: 1 (MIRA 74);
- 91-365d: 13;
- >365d: 71;
- unknown=0.

BD certificado:
- 14 SHALLOW_UNAVAILABLE;
- XUSD sem histórico;
- LA tem 2 linhas e seam de 23 dias.

Próxima ação: investigar causa externa/aliases dos residuais em modo read-only; não alterar lifecycle/readiness sem evidência.
```
