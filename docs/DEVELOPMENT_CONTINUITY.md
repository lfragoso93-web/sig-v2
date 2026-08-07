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
- #249 — readiness explícito do bootstrap.
- #250 — orquestrador global do bootstrap.

## Regra canônica de providers

Política detalhada: `docs/PROVIDER_ACCESS_POLICY_2026-08.md`.

Antes da primeira carteira real, o banco deve estar carregado e reconciliado por bootstrap certificado. Depois disso:

- requests funcionais e cálculos financeiros são DB-first;
- provider recorrente somente para preço intraday e fechamento diário;
- lacuna comprovada de preço em data específica pode consultar apenas a janela mínima necessária, persistir o resultado e então refazer leitura DB-first;
- `get_price_at_date()` permanece leitor puro;
- CRUD de usuário/transações não dispara onboarding, seed ou backfill externo;
- catálogo, metadados, Proventos, eventos, benchmarks e câmbio não são sincronizados por jobs recorrentes.

## Liveness, bootstrap e readiness

Esses conceitos são distintos:

1. `/health` indica que o processo e suas dependências básicas estão vivos e também expõe o estado do bootstrap.
2. `system-bootstrap.v1` pode concluir suas etapas atualmente autorizadas e ficar `bootstrap_complete=true`.
3. Isso **não** libera dados reais enquanto #248 não incorporar e certificar todos os domínios obrigatórios.
4. `/ready` retorna sucesso somente quando `ready_for_real_data=true`.

Estados do bootstrap em memória: `not_started`, `running`, `ready`, `failed`.

O campo `certified_for_real_data` permanece `false` no bootstrap parcial atual. Portanto, um `system-bootstrap.v1` verde não é autorização de go-live.

## Estado certificado localmente — 07/08/2026

HEAD certificado pelo usuário: `b04dffc2839a824ecf5a50ce2ac6583c03c230f7`.

Validação Docker:

- build do backend aprovado;
- suíte dirigida: **18 passed**;
- `python -m compileall -q app tests`: aprovado;
- import integral de `app.main`: aprovado;
- working tree reportada limpa.

## Estado implementado após esse checkpoint — pendente de validação local

### #250 — bootstrap global

- `_boot_sequence()` procedural removida do `app.main`;
- entrada única `run_system_bootstrap()`;
- contrato `system-bootstrap.v1` com relatório por etapa e fail-fast;
- etapas atuais: catálogo de ativos, catálogo/reconciliação/histórico do Tesouro, histórico global de preços e benchmarks;
- Proventos, eventos corporativos e câmbio ainda não foram incorporados por dependerem dos respectivos gates.

### #249 — readiness explícito

- serviço `system_readiness_service.py` com estado em memória;
- separação entre `bootstrap_complete` e `ready_for_real_data`;
- bootstrap parcial nunca certifica dados reais;
- `/health` preserva função de liveness e inclui snapshot do bootstrap;
- `/ready` retorna 503 enquanto a certificação operacional estiver incompleta;
- testes estruturais protegem a fronteira.

## Scheduler

O scheduler recorrente está limitado a:

- preço intraday;
- fechamento diário de preços, restrito à data corrente;
- fechamento diário do Tesouro;
- manutenção local de snapshots/TWR.

Não agenda catálogo, benchmarks, Proventos, eventos, logos ou backfill histórico amplo.

## Ordem objetiva dos próximos blocos

1. Validar localmente #249/#250 e os gates anteriores.
2. Após validação, fechar #249 e a primeira etapa de #250.
3. Implementar resolvedor pontual de lacuna histórica de preço sem alterar `get_price_at_date()`.
4. Converter `assets`/sugestão de catálogo para DB-first e remover consultas externas indevidas.
5. Incorporar ao bootstrap os domínios restantes apenas quando seus gates forem autorizados e idempotentes.
6. Concluir #248 e somente então permitir `ready_for_real_data=true`.
7. Retomar #226 → #216 → #158 depois da certificação estrutural.
8. Somente depois iniciar #246 + #57 (Metas + Análise).

## Prompt mínimo para nova conversa

```text
@GitHub Continue o SGI v2 seguindo `docs/DEVELOPMENT_CONTINUITY.md`.

Repo: lfragoso93-web/sig-v2
Branch: stable-15jun
Gate-mãe: #227
Auditoria: #247
Bootstrap/providers: #248
Readiness: #249
Orquestrador: #250

Preserve a regra:
- bootstrap completo antes de dados reais;
- runtime externo apenas intraday/fechamento;
- exceção somente para lacuna de preço em data específica, com persistência antes do uso;
- demais módulos DB-first;
- não tocar em `goals` antes de #246/#57.
```
