# Roadmap atual do SGI v2

> Revisado em 02/11/2026. Este é o índice vivo de próximas atividades. Inventários antigos permanecem em `history/` e não representam o estado atual das Issues, PRs ou do runtime.

## Ambientes e releases

- Desenvolvimento e validação local: Windows, branch `stable-15jun`.
- Produção: OCI, branch `main`.
- Alterações passam por validação local e Pull Request para `main`. O merge com CI aprovado dispara o deploy automático, com backup pré-deploy e verificação de identidade, smoke e `/ready`.
- O SHA implantado mais recentemente confirmado nesta revisão é `18bac9ba49ff660b4d08818fac8e7a39680380c8` (PR #500). Cada novo SHA exige a certificação correspondente; `/ready` permanece fail-closed.
- A branch desta atividade parte de `stable-15jun` e incorpora `origin/main` antes da validação; os ponteiros remotos não são reescritos.

## Entregas concluídas

- CI/CD de produção por merge em `main`, com backup antes do deploy e verificações pós-deploy.
- Sincronização recorrente de proventos (segunda a sábado, 08:00) e eventos corporativos (dias úteis, 22:00), além dos benchmarks pela manhã e à noite.
- Limite de reset de senha por usuário e desbloqueio auditado pelo SuperAdmin.
- Revisão das dependências compatíveis e correções do workflow OCI nas PRs recentes.
- Inventário remoto consultado em 02/11/2026: zero Issues abertas, zero PRs abertas e zero alertas Dependabot abertos. PR #498 foi fechada por incompatibilidade do salto para TypeScript 7; a atualização compatível do toolchain permanece em #497.
- Os eventos corporativos permanecem como fatos globais; reconciliação e efeito sobre carteira continuam fail-closed quando falta evidência.

## Bloco concluído: automação confiável e documentação

- O painel SuperAdmin mostra a próxima execução e o resultado técnico mais recente dos jobs, com alerta visual para falha e indisponibilidade do Redis.
- Redis retém estado por até 90 dias; apenas o tipo da exceção é exposto. O texto da exceção não é persistido no status.
- Falhas são relançadas ao APScheduler após o registro e não aparecem como execução bem-sucedida.
- A auditoria mensal da fonte B3 permanece opt-in até confirmação da URL e do ano oficiais. O job é read-only; promoção do calendário segue uma etapa separada.
- O módulo legado não registrado de `rate_history` foi removido. A ingestão ativa usa o `benchmark_rate_service` pelo scheduler canônico.
- Este documento é a referência viva. Roadmaps e diagnósticos pontuais antigos estão identificados como históricos.

## Próximas atividades após este bloco

1. Atualizar a referência anual da fonte B3 quando a bolsa publicar novo calendário e, então, revisar a ativação da auditoria mensal.
2. Se o painel de jobs não for suficiente para a operação, escolher um canal e destinatários para alertas externos antes de implementar envio automático.
3. Retomar a revisão incremental de segurança e autorização pelo backlog vigente, evitando reabrir oportunidades já corrigidas nos relatórios de outubro.

## Decisões mantidas

- Não ativar transactional outbox sem um efeito externo ou não reconstruível que precise de entrega durável.
- Não aplicar automaticamente eventos `CONFLICT`, `UNRECONCILED` ou sem evidência suficiente ao ledger/projeções.
- Não confundir status técnico de execução de um job com cobertura, correção ou certificação dos dados obtidos.

## Fontes de verdade

- [`README.md`](../README.md): visão do produto e papéis dos ambientes.
- [`RELIABLE_ASYNC.md`](RELIABLE_ASYNC.md): locks e tarefas assíncronas.
- [`MARKET_CALENDAR_CONTRACT.md`](MARKET_CALENDAR_CONTRACT.md): auditoria e promoção do calendário B3.
- [`USER_VALIDATION_RUNBOOK.md`](USER_VALIDATION_RUNBOOK.md): validação local e PR.
- [`deployment/oci-execution-index.md`](deployment/oci-execution-index.md): release OCI.
- [`DIAGNOSTICO_OPORTUNIDADES_MELHORIA.md`](DIAGNOSTICO_OPORTUNIDADES_MELHORIA.md): diagnóstico histórico, não inventário atual.
