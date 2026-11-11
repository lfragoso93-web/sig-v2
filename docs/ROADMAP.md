# Roadmap atual do SGI v2

> Revisado em 09/11/2026. Este é o índice vivo de próximas atividades. Inventários antigos permanecem em `history/` e não representam o estado atual das Issues, PRs ou do runtime.

## Ambientes e releases

- Desenvolvimento e validação local: Windows, branch `stable-15jun`.
- Produção: OCI, branch `main`.
- Alterações passam por validação local e Pull Request para `main`. O merge com CI aprovado dispara o deploy automático, com backup pré-deploy e verificação de identidade, smoke e `/ready`.
- O SHA implantado mais recentemente confirmado nesta revisão é `93f7a2b2` (PR #543). Cada novo SHA exige a certificação correspondente; `/ready` permanece fail-closed.
- A branch desta atividade parte de `stable-15jun` e incorpora `origin/main` antes da validação; os ponteiros remotos não são reescritos.

## Entregas concluídas

- **Release de Produção PR #543 / SHA `93f7a2b2`:** Deploy validado via GitHub Actions na infraestrutura OCI com certificação aprovada.
- **Regra Obrigatória de Documentação Contínua e Viva:** Estabelecido o invariante de que qualquer instrução, refatoração, funcionalidade ou migração deve atualizar toda a documentação relevante (READMEs, ROADMAP, DOCUMENTACAO_DO_SISTEMA e manuais) no mesmo bloco de trabalho.
- **Suite Avançada de Ferramentas e IA (PRs #518, #521, #522, #523, #532):**
  - Comparador de Ativos com visualização simultânea de até 5 ativos lado a lado;
  - Página dedicada de Análise de Ativos com deep linking por ticker, gráficos de cotação e múltiplos;
  - Carteiras Recomendadas por IA com estratégias de Patrimônio, Proventos e Performance, acompanhadas de simulador matemático de aportes.
- **Central de Ajuda e Assistente Documental com IA (PRs #517, #526, #528):** Central de ajuda redesenhada, busca por tópicos, atalhos de navegação e assistente documental treinado exclusivamente no corpus de `backend/help_docs/` com zero exposição de dados de custódia.
- **Resiliência de Snapshots e Exclusão em Lote de Transações:**
  - Coordenador *single-flight* com coalescência pela menor data por carteira (`portfolio_snapshot_rebuild_queue`), eliminando contenção de locks e exaustão do pool em rajadas de mutações.
  - Exclusão em lote no backend (`POST /transactions/bulk-delete`) e UI (`Transacoes.tsx`) com seleção múltipla e limpeza por grupo filtrado.
- **Aprimoramento Contábil de Eventos Corporativos e Importações B3:**
  - Segregação de débitos de frações em grupamento (reverso) no adaptador B3, eliminando dupla dedução de quantidade.
  - Desambiguação de devoluções de aluguel de ações (BTC) vs compras a mercado com preservação de preço médio (PM).
  - Painel de Eventos Corporativos e Leilão de Frações no frontend com discriminação clara entre frações pendentes aguardando leilão e valores liquidados em conta.
- **Evolução Patrimonial Contínua e Ponto Intradiário (PR #533):** Snapshots diários consolidados aos finais de semana e feriados somados a ponto intradiário em tempo real no gráfico do Dashboard com cotações correntes.
- **Aprimoramento do Livro-Razão e Transações (PRs #532, #543):** Extrato com filtro por período, máscara decimal monetária da direita para a esquerda (padrão R$) e suporte formal a lançamentos com custo unitário R$ 0,00 (bonificações e doações).
- **Unificação de Ações Fracionárias B3 (PRs #524, #529):** Normalização contábil unificando códigos fracionários (sufixo `F`) ao lote padrão no backend, catalog e UI.
- **Governança do Scheduler e Painel SuperAdmin (PRs #501, #520):** Monitoramento dos 12 jobs em tempo real, capacidade de disparo manual sob demanda e histórico detalhado de execuções com logs.
- **Expansão Rigorosa do `PortfolioAccessContext` (PRs #503-#516):** Autorização por escopo de carteira aplicada a transações, IRPF, proventos, performance, metas e CLIs de certificação.
- **Purga de Entidades Sintéticas (PRs #525, #531):** Migrações Alembic `20261105_clean_cert_entities` e `20261105_purge_cert_entities` expurgando dados sintéticos de teste do banco de produção.
- **Branding Institucional SGI e Nova Landing Page (PRs #527, #530):** Alinhamento completo da marca SGI, eliminação de tokens legados e nova Landing Page responsiva.
- CI/CD de produção por merge em `main`, com backup antes do deploy e verificações pós-deploy.
- Sincronização recorrente de proventos (segunda a sábado, 08:00) e eventos corporativos (dias úteis, 22:00), além dos benchmarks pela manhã e à noite.
- Limite de reset de senha por usuário e desbloqueio auditado pelo SuperAdmin.

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
