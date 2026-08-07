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

A Issue #227 é o gate-mãe antes de dados reais. A Issue #247 executa a auditoria atual e a #248 concentra o bootstrap certificado e a fronteira única de providers.

## Regra canônica de providers

Política detalhada: `docs/PROVIDER_ACCESS_POLICY_2026-08.md`.

Antes de criar/importar carteiras reais, o sistema deve executar um bootstrap idempotente e certificável que carregue no banco todo o conjunto necessário: catálogo, metadados, históricos, Proventos, eventos corporativos, Tesouro, benchmarks, câmbio e séries auxiliares.

Depois que o ambiente estiver pronto:

- requests funcionais e cálculos financeiros são DB-first;
- providers externos só podem ser consultados de forma recorrente para **preço intraday** e **preço de fechamento diário**;
- existe uma única exceção adicional: se uma data necessária não tiver cobertura de preço persistida, um resolvedor dedicado pode consultar a janela mínima daquela data, persistir o preço e então refazer a leitura DB-first;
- `get_price_at_date()` permanece leitor puro e nunca chama provider;
- busca de ativos, detalhes, posições, Proventos, IRPF, rentabilidade e relatórios não consultam providers diretamente;
- CRUD de usuário/transações não dispara seed, onboarding ou backfill externo;
- nenhum valor externo não persistido pode alimentar diretamente cálculo financeiro.

A aplicação não está pronta para dados reais apenas porque o FastAPI iniciou; o bootstrap precisa estar concluído e validado.

## Regra temporária para Metas

A Issue #241 está concluída. `goals` permanece como exceção deliberada da convergência Alembic/ORM. Até #246 + #57:

- não criar migration para `goals` apenas para limpar `alembic check`;
- não alterar tipos, colunas, constraints ou enums sem redesenho funcional prévio;
- não promover o módulo atual como contrato canônico estabilizado.

## Ordem vigente

### AGORA

1. #247 — continuar auditoria de routers, serviços, endpoints, aliases e integrações.
2. #248 — consolidar bootstrap certificado, readiness e fronteira única de providers.
3. Remover consultas externas recorrentes fora de intraday/fechamento e da exceção pontual por data.
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

### Último checkpoint certificado localmente

HEAD certificado: `371b7e5513e3d0350a0529f57051a17f30f4a237`.

Validação executada em Docker:

- rebuild do backend aprovado;
- suíte dirigida com `performance`, `positions`, `transactions`, `prices` e import estrutural: **11 passed**;
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
- a política de providers foi formalizada em documento próprio;
- o scheduler recorrente foi reduzido a preço intraday, fechamento diário de preços/Tesouro e manutenção local de snapshots;
- catálogo, benchmarks, Proventos, eventos, logos e metadados não são mais sincronizados por jobs recorrentes;
- `asset_service` deixou de orientar callers a disparar onboarding automático.

### Operação

- CRUD de transações não inicia ingestão externa automática.
- GETs financeiros auditados permanecem DB-first.
- o boot atual ainda não implementa integralmente o novo contrato de bootstrap/readiness; isso está rastreado pela #248;
- criação/importação de carteiras reais permanece bloqueada até bootstrap certificado;
- Proventos real (#226), gate de seeds/bootstrap (#216) e rebuild (#158) permanecem bloqueados.

## Próximo bloco objetivo

1. Validar localmente o novo gate `test_scheduler_provider_boundary.py` junto aos gates anteriores.
2. Implementar em #248 a porta única de bootstrap e seu relatório estruturado/readiness, reaproveitando serviços idempotentes existentes.
3. Implementar resolvedor pontual de lacuna histórica sem alterar a pureza de `get_price_at_date()`.
4. Revisar `assets` para que catálogo/sugestão sejam DB-first, preservando apenas cotação intraday como acesso externo autorizado.
5. Fechar a prova de consumidores do router placeholder `quotes`.
6. Revisar `portfolios`, `admin`, `irpf`, `class_targets`, `dividends` e clients frontend restantes.
7. Não iniciar #246/#57 nem cargas reais antes da certificação estrutural.

## Prompt mínimo para nova conversa

```text
@GitHub Continue o desenvolvimento do SGI v2 seguindo integralmente
`docs/DEVELOPMENT_CONTINUITY.md`.

Repositório: lfragoso93-web/sig-v2
Branch obrigatória: stable-15jun
Issue executora: #247
Bootstrap/provider policy: #248
Gate-mãe: #227

Regra central:
- antes de carteiras reais, executar bootstrap completo e persistente;
- em runtime, provider externo somente para preço intraday e fechamento diário;
- exceção: lacuna de preço em data específica pode consultar janela mínima, persistir e refazer leitura DB-first;
- todos os demais módulos devem ser DB-first.

Preserve `goals` como exceção deliberada e não crie migration para esse domínio.
```
