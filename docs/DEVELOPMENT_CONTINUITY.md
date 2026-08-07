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

O SGI v2 está em **auditoria arquitetural pós-convergência e consolidação do bootstrap inicial**.

A Issue #227 é o gate-mãe antes de dados reais. A Issue #247 executa o trabalho imediato.

## Regra canônica de providers

Antes de criar/importar carteiras reais, o sistema deve executar um bootstrap idempotente e certificável que carregue no banco todo o conjunto necessário: catálogo, metadados, históricos, Proventos, eventos corporativos, Tesouro, benchmarks, câmbio e séries auxiliares.

Depois que o ambiente estiver pronto:

- requests funcionais e cálculos financeiros são DB-first;
- providers externos só podem ser consultados de forma recorrente para **preço intraday** e **preço de fechamento diário**;
- o preço externo deve ser persistido antes de alimentar contratos financeiros;
- busca de ativos, detalhes, posições, Proventos, IRPF, rentabilidade e relatórios não consultam providers diretamente;
- CRUD de usuário/transações não dispara seed, onboarding ou backfill externo.

A aplicação não está pronta para dados reais apenas porque o FastAPI iniciou; o bootstrap precisa estar concluído e validado.

## Regra temporária para Metas

A Issue #241 está concluída. `goals` permanece como exceção deliberada da convergência Alembic/ORM. Até #246 + #57:

- não criar migration para `goals` apenas para limpar `alembic check`;
- não alterar tipos, colunas, constraints ou enums sem redesenho funcional prévio;
- não promover o módulo atual como contrato canônico estabilizado.

## Ordem vigente

### AGORA

1. #247 — continuar auditoria de routers, serviços, endpoints, aliases e integrações.
2. Remover consultas externas fora da fronteira intraday/fechamento.
3. Consolidar desenho de bootstrap inicial e readiness.
4. Confirmar pendências reais de #129 e somente itens necessários de #130/#127.
5. Certificar a auditoria com testes, build/import e documentação sincronizada.

### DEPOIS

6. #150 — histórico persistido do IBOV.
7. #149 — TWR dedicado de Tesouro Direto e Renda Fixa.

### BLOQUEADO ATÉ CERTIFICAÇÃO

8. #226 — duas execuções reais controladas de Proventos.
9. #216 — gate agregado de seeds/bootstrap.
10. #158 — CSV, posições, snapshots e reconciliação.
11. primeira criação/importação de carteira real.

### PRÓXIMA GRANDE FASE FUNCIONAL

12. #246 + #57 — Metas + Análise de Carteira.

## Estado atual — 07/08/2026

### Baseline certificado localmente

HEAD certificado antes do ciclo documental atual: `08414af3a7b570ae9753e83ba5eecf2c17f20e42`.

Validação executada em Docker:

- rebuild do backend aprovado;
- 7 testes do checkpoint de auditoria aprovados;
- `python -m compileall -q app tests`: aprovado;
- import integral de `app.main`: aprovado;
- working tree local limpa.

### Auditoria Etapa 2

Já corrigido/publicado:

- `prices` é leitura DB-first e possui gate contra provider/backfill no request;
- `transactions` não dispara onboarding, preços, logos, eventos ou backfill de Proventos automaticamente após POST/PATCH;
- `performance` não expõe mais POST público de rebuild de snapshots;
- `positions` não aceita mais `refresh=true` e não atualiza cotações durante GET financeiro;
- gates estruturais protegem essas fronteiras;
- `rentabilidade` foi classificado como superfície GET/DB-first;
- `quotes` é placeholder redundante candidato a remoção após prova final de consumidores;
- `assets` ainda possui endpoints que consultam providers e agora devem ser reavaliados contra a nova regra canônica: somente intraday e fechamento podem permanecer externos.

### Operação

- CRUD de transações não inicia ingestão externa automática.
- GETs financeiros auditados permanecem DB-first.
- o boot atual ainda não implementa integralmente o novo contrato de bootstrap/readiness; isso passa a ser pendência arquitetural explícita;
- criação/importação de carteiras reais permanece bloqueada até bootstrap certificado;
- Proventos real (#226), gate de seeds/bootstrap (#216) e rebuild (#158) permanecem bloqueados.

## Próximo bloco objetivo

1. Validar localmente os gates já publicados de `performance` e `positions` junto aos anteriores.
2. Revisar `assets`, `quotes_service`, scheduler e entrypoint contra a regra: provider recorrente somente para intraday/fechamento.
3. Fechar a prova de consumidores do router placeholder `quotes`.
4. Desenhar o bootstrap inicial único, idempotente e o estado de readiness antes de liberar carteiras reais.
5. Revisar `portfolios`, `admin`, `irpf`, `class_targets`, `dividends` e clients frontend restantes.
6. Não iniciar #246/#57 nem cargas reais antes da certificação estrutural.

## Prompt mínimo para nova conversa

```text
@GitHub Continue o desenvolvimento do SGI v2 seguindo integralmente
`docs/DEVELOPMENT_CONTINUITY.md`.

Repositório: lfragoso93-web/sig-v2
Branch obrigatória: stable-15jun
Issue executora: #247
Gate-mãe: #227

Regra central:
- antes de carteiras reais, executar bootstrap completo e persistente;
- em runtime, provider externo somente para preço intraday e fechamento diário;
- todos os demais módulos devem ser DB-first.

Preserve `goals` como exceção deliberada e não crie migration para esse domínio.
```
