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

O SGI v2 está em estabilização arquitetural final antes da próxima grande fase funcional.

Até o encerramento da Issue #227:

- não importar novas carteiras reais sem autorização explícita;
- não criar novos usuários reais;
- tratar dados atuais como desenvolvimento descartável;
- usar fixtures, factories e bancos descartáveis;
- manter seeds, sincronizações e rebuilds externos explicitamente opt-in;
- não retomar a certificação operacional da #158 fora dos gates vigentes.

## Regra arquitetural temporária para Metas

O domínio `goals` é exceção consciente da convergência Alembic/ORM encerrada pela #241.

Até o início do macroprojeto #246 + #57:

- não criar migration para `goals` apenas para limpar `alembic check`;
- não alterar tipos, colunas, constraints ou enums de `goals` sem o redesenho funcional prévio;
- não promover o módulo atual como contrato canônico estabilizado;
- preservar a tabela histórica e tratar o diff remanescente como dívida arquitetural rastreada.

## Ordem vigente

1. Encerrar formalmente a #241 e sincronizar documentação final.
2. Auditar arquitetura global, serviços, routers, endpoints e legado remanescente.
3. Preparar e abrir PR estrutural `stable-15jun` → `main`.
4. Consolidar eventuais pendências restantes de eventos corporativos (#129/#130/#127).
5. IBOV e TWR — #150 e #149.
6. Ingestão, seeds e rebuild determinísticos — #158, #216 e #226, respeitando #227.
7. Somente após estabilização definitiva iniciar Metas + Análise de Carteira (#246 + #57).

## Checklist de início de conversa

1. Ler esta documentação.
2. Consultar a Issue #227 e os comentários mais recentes quando o bloco tocar operação real.
3. Confirmar branch e HEAD remoto de `stable-15jun`.
4. Comparar `main...stable-15jun` e confirmar ausência de divergência para trás.
5. Consultar Issues relacionadas ao bloco atual.
6. Consultar todas as PRs abertas, inclusive Dependabot.
7. Conferir README, ROADMAP, CHANGELOG e `docs/architecture.md`.
8. Confirmar o último resultado de build, testes, Ruff e `compileall` registrado.
9. Não repetir perguntas já respondidas no histórico ou nas Issues.
10. Prosseguir do próximo bloco objetivo registrado neste documento e na Issue ativa.

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

## Estado atual do plano — 07/08/2026

### Backend e arquitetura

- HEAD estrutural de referência antes da sincronização documental: `17beeb9e6ae70f51d523e273bebda368872f81de`.
- Build Docker: aprovado.
- `compileall`: aprovado.
- Suíte estrutural final: 15 testes aprovados.
- `app.main` importado integralmente.
- Consumers legados de `AppConfig` e `IRPFReport` removidos e protegidos por gates.
- Transactions alinhado ao contrato físico migrado.
- Proventos, Eventos Corporativos, IRPF e Snapshots consolidados.
- `fx_rates` participa do MetaData e o leitor USD/BRL é exclusivamente DB-first.
- Alembic endurecido por gates contra autogenerate monolítico e remoções acidentais.
- `alembic check` remanescente limitado exclusivamente a `goals`.
- #246 criada para redesenho de Metas em conjunto com #57.

### Frontend

- IRPF permanece integrado aos contratos canônicos.
- A rota `/carteira/metas` continua existente como superfície atual, mas o domínio subjacente não é considerado contrato canônico estabilizado.
- `/irpf` e `/metas` permanecem redirects legados temporários.
- O redesenho futuro de Metas e Análise deve revisar frontend, contratos e navegação como um único macroprojeto.

### Operação

- Boot de sincronização de mercado permanece desabilitado por padrão.
- Seeds, rebuilds e cargas reais permanecem suspensos pelos gates vigentes da #227.
- `stable-15jun` está à frente de `main` e sem commits para trás no checkpoint de 07/08/2026.

## Próximo bloco objetivo

1. Finalizar sincronização de ROADMAP, README, CHANGELOG, arquitetura e esta continuidade.
2. Atualizar e encerrar formalmente a #241 com a exceção `goals` registrada.
3. Executar auditoria arquitetural global de serviços, routers, endpoints, duplicações e legado remanescente.
4. Corrigir achados em blocos pequenos, mantendo Issues e documentação sincronizadas.
5. Após a auditoria e certificação, abrir a PR estrutural `stable-15jun` → `main`.
6. Não iniciar #246/#57 antes dessa estabilização.

## Prompt mínimo para nova conversa

```text
@GitHub Continue o desenvolvimento do SGI v2 seguindo integralmente
`docs/DEVELOPMENT_CONTINUITY.md`.

Repositório: lfragoso93-web/sig-v2
Branch obrigatória: stable-15jun

Antes de alterar código:
- confirme o HEAD remoto;
- compare stable-15jun com main;
- leia a Issue do bloco atual e #227 quando houver impacto operacional;
- revise PRs abertas e documentação viva;
- preserve `goals` como exceção da #241 e não crie migration para esse domínio;
- recupere o último checkpoint e prossiga do próximo bloco objetivo.
```
