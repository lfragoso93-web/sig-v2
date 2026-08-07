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

O SGI v2 está em **governança e estabilização arquitetural antes da próxima fase funcional**.

A Issue #227 é o gate-mãe antes de dados reais. A Issue #247 é a executora do trabalho imediato.

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

1. #247 — reconciliar documentação viva, Issues e PRs.
2. #247 — auditar arquitetura global, serviços, routers, endpoints, aliases, integrações e legado.
3. Confirmar pendências reais de #129 e somente os itens necessários de #130/#127.

### DEPOIS

4. #150 — histórico persistido do IBOV.
5. #149 — TWR dedicado de Tesouro Direto e Renda Fixa.

### BLOQUEADO ATÉ CERTIFICAÇÃO

6. #226 — duas execuções reais controladas de Proventos.
7. #216 — gate agregado de seeds.
8. #158 — CSV, posições, snapshots e reconciliação.

### PRÓXIMA GRANDE FASE FUNCIONAL

9. #246 + #57 — Metas + Análise de Carteira.

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

### Backend e arquitetura

Baseline estrutural de referência: `17beeb9e6ae70f51d523e273bebda368872f81de`.

- Build Docker: aprovado.
- `compileall`: aprovado.
- Suíte estrutural final: 15 testes aprovados.
- `app.main` importado integralmente.
- Consumers legados de `AppConfig` e `IRPFReport` removidos e protegidos por gates.
- Transactions alinhado ao contrato físico migrado.
- Proventos, Eventos Corporativos, IRPF e Snapshots consolidados.
- `fx_rates` participa do MetaData e o leitor USD/BRL é exclusivamente DB-first.
- Alembic endurecido por gates contra autogenerate monolítico e remoções acidentais.
- #241 encerrada; diff remanescente limitado a `goals` por decisão arquitetural.

Commits posteriores ao baseline nesta etapa foram apenas de governança/documentação e não alteraram runtime ou schema.

### Frontend

- IRPF permanece integrado aos contratos canônicos.
- `/carteira/metas` existe como superfície atual, mas o domínio não é considerado estabilizado.
- `/irpf` e `/metas` permanecem redirects temporários e serão auditados por consumidor na #247.
- Análise de Carteira não deve ser tratada como backend funcional concluído; o router atual será revisitado apenas em #246 + #57.

### Operação

- Boot de sincronização de mercado permanece desabilitado por padrão.
- Seeds, rebuilds e cargas reais permanecem suspensos pela #227.
- Proventos real (#226), gate de seeds (#216) e rebuild (#158) permanecem bloqueados.

## Próximo bloco objetivo

1. Concluir a sincronização documental da Etapa 1 da #247.
2. Atualizar Issues abertas que ainda contenham estado comprovadamente obsoleto.
3. Registrar no CHANGELOG a reorganização de governança.
4. Encerrar a Etapa 1 da #247 quando todos os critérios estiverem atendidos.
5. Só então iniciar a auditoria técnica da Etapa 2.
6. Não iniciar #246/#57 nem cargas reais antes dessa estabilização.

## Prompt mínimo para nova conversa

```text
@GitHub Continue o desenvolvimento do SGI v2 seguindo integralmente
`docs/DEVELOPMENT_CONTINUITY.md`.

Repositório: lfragoso93-web/sig-v2
Branch obrigatória: stable-15jun

Antes de alterar código:
- confirme o HEAD remoto;
- compare stable-15jun com main;
- leia #247 e #227;
- revise todas as PRs abertas e a documentação viva;
- preserve `goals` como exceção deliberada e não crie migration para esse domínio;
- prossiga da ordem canônica: governança → auditoria → performance → operação → Metas+Análise.
```
