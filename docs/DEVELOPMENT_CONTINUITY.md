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
- #267 — universo CRIPTO suportado limitado às Top 100 por capitalização.
- #254 — integração estrutural de eventos corporativos ao bootstrap — wrapper, testes e integração v4 publicados; validação integrada ainda pendente.
- #265 — shallow histories CRIPTO — **concluída em 11/08/2026** com fila rasa zerada no universo amplo auditado.
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

## Política CRIPTO Top 100 — #267

A existência de um símbolo no catálogo BRAPI não significa suporte operacional automático pelo SGI.

Contrato canônico:

1. CoinGecko `/coins/markets` define a relevância por capitalização de mercado;
2. são considerados no máximo os Top 100 por `market_cap_rank`;
3. o universo suportado é a interseção desse Top 100 com os símbolos disponíveis no catálogo CRIPTO da BRAPI;
4. CoinGecko é usado somente no bootstrap para ranking de relevância; BRAPI permanece a integração de disponibilidade/cotações do SGI;
5. ativos CRIPTO já persistidos fora do universo suportado são preservados e auditáveis, sem alteração artificial de lifecycle;
6. seed, backfill histórico inicial e readiness CRIPTO devem usar o mesmo universo suportado;
7. ativos fora desse universo não bloqueiam readiness CRIPTO.

Não foi criada migration nem campo novo em `assets` neste bloco. O contrato é derivado dinamicamente durante bootstrap/readiness para evitar persistência estrutural prematura antes da validação operacional.

## Checkpoint CRIPTO amplo anterior — 11/08/2026

BC/BD foram certificados localmente no HEAD `9772b8c2bdb9875d85abc4a72ed0bebea39c222e` sobre o catálogo amplo anterior de 481 ativos.

Validação local:

- build Docker aprovado;
- testes dirigidos BC/BD: **2 passed**;
- `python -m compileall -q app tests`: aprovado;
- import integral de `app.main`: aprovado;
- `git diff --check`: aprovado;
- working tree limpa;
- duplicidades globais em `(asset_id, timestamp)`: 0.

Distribuição ampla:

- total: 481 ativos;
- `HISTORY_START_EXHAUSTED = 369`;
- `HISTORY_START_COMPLEMENT_GAPPED = 87`;
- `HISTORY_START_SHALLOW_UNAVAILABLE = 14`;
- `HISTORY_START_SHALLOW_VERIFIED = 10`;
- `HISTORY_UNAVAILABLE = 1` (`XUSD`);
- `shallow_histories = 0`;
- `blocking_seams = 88`.

BC classificou os 87 gaps como:

- `<= 30 dias`: 2 (`GALA = 22`, `WLFI = 27`);
- `31–90 dias`: 1 (`MIRA = 74`);
- `91–365 dias`: 13;
- `>365 dias`: 71;
- `unknown`: 0.

BD confirmou 14 `HISTORY_START_SHALLOW_UNAVAILABLE` e 1 `HISTORY_UNAVAILABLE` (`XUSD`). O finding mostrou que o catálogo amplo continha ativos sem relevância operacional suficiente e motivou a #267.

Esses estados permanecem evidência histórica e auditável. Eles não devem ser apagados nem reclassificados apenas para produzir readiness verde.

## Implementação estrutural #267 publicada

Commits:

- `3f7de4d5ad21ed80f5c822f54d620a84139c8082` — adapter CoinGecko de ranking Top 100 por market cap;
- `6d030ccc79a4350fe317d12521b2496157afac1a` — contrato de universo suportado Top 100 ∩ BRAPI;
- `58467c7f1377b57752af2204bf0b10767f8d347d` — clareza/import explícito do contrato;
- `50bbbe92fa70e5473e1710ad147041ea31e5e6db` — seed CRIPTO limitado ao universo suportado;
- `d8f8d7f6f4ee29a022b97c922b856279f9276259` — gate do boundary do seed;
- `5cce32e9d2fa374fcba9b861ce9314c24beb698c` — testes unitários da interseção/deduplicação;
- `e0dc9e86d85a7461e7ccff8477cbdf1a3af702c8` — histórico CRIPTO do bootstrap limitado ao universo suportado;
- `4597939f687bf3104645a2520028675867e245ac` — readiness CRIPTO limitado ao universo suportado;
- `5d67b7a3d0ec726ae3c61a404ef2f9177c98475c` — seam audit com escopo opcional de tickers;
- `fa7d733c8e43c34fee21cf3af8f757fd08e60a52` — shallow audit com escopo opcional de tickers.

Nenhum desses blocos:

- apaga ativos CRIPTO antigos;
- reclassifica `provider_status` para mascarar findings;
- altera schema/migration;
- libera `ready_for_real_data`;
- adiciona provider a requests financeiros.

## Estado estrutural do bootstrap

`system-bootstrap.v4` continua sendo o orquestrador global. O estágio `asset_price_history` agora resolve o universo CRIPTO suportado e chama o backfill global com `asset_types={CRIPTO}` e `tickers=<universo suportado>`. As demais classes com providers dedicados continuam em seus estágios/contratos próprios já existentes.

Readiness CRIPTO agora reporta:

- `universe_policy = top_100_market_cap_coingecko_intersect_brapi`;
- `supported_universe_size`;
- contagens de histórico, duplicidades, statuses bloqueantes, seams e shallow histories somente no universo suportado.

A certificação operacional dessa nova política ainda está pendente de execução local. `ready_for_real_data` permanece `false`.

## Scheduler

O scheduler recorrente está limitado a:

- preço intraday;
- fechamento diário de preços, restrito à data corrente;
- fechamento diário do Tesouro;
- manutenção local de snapshots/TWR.

Não agenda catálogo, ranking de market cap, benchmarks, Proventos, eventos, logos ou backfill histórico amplo.

## Ordem objetiva dos próximos blocos

1. Validar localmente os testes da #267, `compileall`, Ruff e import de `app.main`.
2. Executar `fetch_supported_crypto_universe()` em ambiente com rede e registrar quantos dos Top 100 CoinGecko estão disponíveis na BRAPI.
3. Executar `pre_prod_crypto_readiness_audit` no novo universo e inventariar apenas findings residuais suportados.
4. Confirmar que ativos fora do universo amplo anterior deixam de bloquear readiness sem alteração de seus registros/lifecycle.
5. Atualizar #267/#248/#250 com a evidência operacional e, se verde, concluir #267.
6. Manter `ready_for_real_data=false` até a certificação final da #248/#227.
7. Continuar #247/#129 para achados residuais de routers/services/providers/aliases.
8. Retomar #226 → #216 → #158 somente depois da certificação estrutural e da autorização operacional apropriada.
9. Somente depois iniciar #246 + #57 (Metas + Análise).

## Prompt mínimo para nova conversa

```text
@GitHub Continue o SGI v2 seguindo `docs/DEVELOPMENT_CONTINUITY.md`.

Repo: lfragoso93-web/sig-v2
Branch: stable-15jun
Gate-mãe: #227
Bootstrap/readiness: #248/#250
Universo CRIPTO: #267

Decisão atual:
- suportar somente Top 100 CRIPTO por market cap;
- ranking CoinGecko;
- universo = Top 100 CoinGecko ∩ catálogo BRAPI;
- preservar ativos legados fora do universo sem deixá-los bloquear readiness;
- `ready_for_real_data=false` até certificação final.

Próxima ação: validar localmente a implementação #267 e executar readiness nominal sobre o novo universo suportado.
```
