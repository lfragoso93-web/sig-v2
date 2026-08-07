# Continuidade de desenvolvimento — SGI v2

> Documento obrigatório para iniciar ou retomar qualquer conversa de desenvolvimento.

## Contexto permanente

- Repositório: `lfragoso93-web/sig-v2`.
- Branch obrigatória: `stable-15jun`.
- Nunca desenvolver diretamente na `main`.
- Antes de qualquer alteração, comparar `stable-15jun` com `main`, revisar Issues abertas, PRs abertas e documentação viva.
- Dividir macroblocos em commits pequenos e rastreáveis.
- Ao final de cada bloco informar resumo técnico, impacto arquitetural, testes, SHA completo e próximo bloco.
- Atualizar a Issue correspondente antes e depois da implementação.
- README, ROADMAP, CHANGELOG e documentação arquitetural devem refletir o estado real.

## Decisão vigente

O SGI v2 está em **auditoria arquitetural pós-convergência**.

A Issue #227 é o gate-mãe antes de dados reais. A Issue #247 executa o trabalho imediato.

Até o encerramento da #227:

- não importar novas carteiras reais sem autorização explícita;
- não criar novos usuários reais;
- tratar dados atuais como desenvolvimento descartável;
- usar fixtures, factories e bancos descartáveis;
- manter seeds, sincronizações e rebuilds externos explicitamente opt-in;
- não retomar a certificação operacional da #158 fora dos gates vigentes.

## Regra arquitetural temporária para Metas

A Issue #241 está concluída. `goals` permanece como exceção deliberada da convergência Alembic/ORM.

Até o início do macroprojeto #246 + #57:

- não criar migration para `goals` apenas para limpar `alembic check`;
- não alterar tipos, colunas, constraints ou enums sem redesenho funcional prévio;
- não promover o módulo atual como contrato canônico estabilizado;
- tratar Metas e Análise como um único macroprojeto futuro.

## Ordem vigente

### AGORA

1. #247 — continuar auditoria de routers, serviços, endpoints, aliases e integrações.
2. Confirmar/remover placeholders e compatibilidades somente com prova de consumidores.
3. Consolidar achados reais de #129 e somente itens necessários de #130/#127.
4. Certificar a auditoria com testes estruturais, build/import e documentação sincronizada.

### DEPOIS

5. #150 — histórico persistido do IBOV.
6. #149 — TWR dedicado de Tesouro Direto e Renda Fixa.

### BLOQUEADO ATÉ CERTIFICAÇÃO

7. #226 — duas execuções reais controladas de Proventos.
8. #216 — gate agregado de seeds.
9. #158 — CSV, posições, snapshots e reconciliação.

### PRÓXIMA GRANDE FASE FUNCIONAL

10. #246 + #57 — Metas + Análise de Carteira.

Backlog não bloqueador: #58, #83, #90, #97 e evoluções amplas de #127/#130 não exigidas por achados da auditoria.

## PRs Dependabot

As PRs Dependabot abertas são fila técnica separada e não alteram a ordem funcional do projeto. Cada uma exige análise de risco, compatibilidade e CI antes de merge.

## Checklist de início de conversa

1. Ler esta documentação.
2. Confirmar branch e HEAD remoto de `stable-15jun`.
3. Comparar `main...stable-15jun` e confirmar ausência de divergência para trás.
4. Ler #247 e #227.
5. Consultar Issues relacionadas ao bloco atual.
6. Consultar todas as PRs abertas, inclusive Dependabot.
7. Conferir README, ROADMAP, CHANGELOG e `docs/architecture.md`.
8. Confirmar o último resultado de build, testes, Ruff e `compileall` registrado.
9. Não repetir perguntas já respondidas no histórico ou nas Issues.
10. Prosseguir da ordem canônica acima.

## Formato de checkpoint

Cada checkpoint deve registrar:

- escopo concluído;
- arquivos e contratos afetados;
- impacto arquitetural;
- testes executados e resultados;
- todos os SHAs do checkpoint;
- Issues e documentação atualizadas;
- riscos ou pendências;
- recomendação objetiva do próximo bloco;
- HEAD remoto esperado.

## Estado atual — 07/08/2026

### Baseline certificado localmente

HEAD certificado antes do ciclo atual: `08414af3a7b570ae9753e83ba5eecf2c17f20e42`.

Validação executada em Docker:

- rebuild do backend aprovado;
- `test_transactions_no_automatic_market_sync.py` + `test_price_history_router_db_first.py` + `test_removed_model_consumers_and_main_import.py`: **7 passed**;
- `python -m compileall -q app tests`: aprovado;
- import integral de `app.main`: aprovado;
- working tree local limpa.

### Auditoria Etapa 2 — alterações posteriores ao baseline

Já corrigido/publicado:

- `prices` é leitura DB-first e possui gate contra provider/backfill no request;
- `transactions` não dispara onboarding, preços, logos, eventos ou backfill de Proventos automaticamente após POST/PATCH;
- `performance` não expõe mais POST público de rebuild de snapshots; serviços internos permanecem para operação explícita;
- `positions` não aceita mais `refresh=true` e não atualiza cotações durante GET financeiro;
- gates estruturais protegem `prices`, `transactions`, `performance` e `positions`;
- `rentabilidade` foi classificado como superfície GET/DB-first;
- `quotes` foi classificado como placeholder redundante candidato a remoção após prova final de consumidores;
- `assets` permanece superfície mista: leitura local + descoberta/provider interativa; essa fronteira não deve vazar para cálculos financeiros.

Documento de inventário: `docs/ROUTER_ENDPOINT_AUDIT_2026-08.md`.

### Frontend

- IRPF permanece integrado aos contratos canônicos.
- `/carteira/metas` existe como superfície atual, mas o domínio não é considerado estabilizado.
- `/irpf` e `/metas` permanecem redirects temporários em auditoria.
- Análise de Carteira continua bloqueada para #246 + #57.
- `performanceService.ts` não expõe a antiga porta de backfill; seu contrato histórico ainda precisa ser comparado com as rotas backend antes de decidir se é client órfão.

### Operação

- Boot de sincronização de mercado permanece desabilitado por padrão.
- CRUD de transações não inicia mais ingestão externa automática.
- GETs financeiros de preços/posições auditados permanecem DB-first.
- Seeds, rebuilds e cargas reais permanecem suspensos pela #227.
- Proventos real (#226), gate de seeds (#216) e rebuild (#158) permanecem bloqueados.

## Próximo bloco objetivo

1. Validar localmente os novos gates de `performance` e `positions` junto aos gates anteriores.
2. Fechar a prova de consumidores do router placeholder `quotes`; remover apenas se ausência estiver comprovada, preservando `quotes_service` interno.
3. Revisar `assets.detail` e a fronteira entre cotação live e leitura financeira persistida.
4. Revisar `portfolios`, `admin`, `irpf` e `class_targets` por mutações/aliases redundantes.
5. Revisar `dividends` e `performanceService.ts` como compatibilidades/client potencialmente órfãos.
6. Não iniciar #246/#57 nem cargas reais antes da certificação estrutural.

## Prompt mínimo para nova conversa

```text
@GitHub Continue o desenvolvimento do SGI v2 seguindo integralmente
`docs/DEVELOPMENT_CONTINUITY.md`.

Repositório: lfragoso93-web/sig-v2
Branch obrigatória: stable-15jun
Issue executora: #247
Gate-mãe: #227

Antes de alterar código:
- confirme o HEAD remoto;
- compare stable-15jun com main;
- leia #247 e #227;
- revise PRs abertas e documentação viva;
- preserve `goals` como exceção deliberada e não crie migration para esse domínio;
- mantenha requests financeiros DB-first e operações externas/rebuilds explicitamente opt-in;
- prossiga do próximo bloco objetivo deste documento.
```
