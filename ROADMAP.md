# Roadmap modular — SGI v2

> Última atualização: 28/07/2026

## Visão geral

| Módulo | Status | Progresso |
|---|---|---:|
| Core backend e autenticação | Estável | 100% |
| Carteiras e transações | Estável | 100% |
| Importação CSV | Estável, revisão pré-produção pendente | 95% |
| Dados canônicos | Consolidado | 100% |
| Histórico B3 COTAHIST | Consolidado | 100% |
| Tesouro Direto — valuation atual | Validado | 100% |
| Renda Fixa — valuation atual | Consolidado | 100% |
| Snapshots consolidados | Consolidado | 100% |
| Snapshots por classe de mercado | Consolidado | 100% |
| Proventos | Fase 2 concluída e promovida pela PR #166 | 100% |
| Página Resumo | Concluída e promovida pela PR #164 | 100% |
| Página Patrimônio | Fase 3 concluída e promovida pela PR #184 | 100% |
| Página Rentabilidade | Contratos concluídos | 95% |
| Dependências | Atualizações compatíveis aplicadas; PR #221 bloqueada por incompatibilidade | 95% |
| Configuração Pydantic v2 | Migração validada e Issue #186 encerrada | 100% |
| Backup/Restore pré-produção | Validação real v3 concluída (#183) | 100% |
| Dry-run de limpeza | Validado no PostgreSQL real (#185) | 100% |
| Exportação pré-produção | Validada e promovida pela PR #191 (#188) | 100% |
| Planejamento seguro da limpeza | Validado pela Issue #195 e PR #194 | 100% |
| Limpeza isolada | Sucesso e rollback reconciliados; PR #198 promovida | 100% |
| Perfil de alvo real | Implementado, validado e promovido pela PR #204 | 100% |
| Seed isolado B3/COTAHIST | Entry point implementado; execução pendente | 90% |
| Seed isolado Tesouro | Identidade, comparador e wrapper implementados; execução real pendente (#208) | 97% |
| Seed isolado de benchmarks | Execução real e idempotência comprovadas (#216) | 100% |
| Seed isolado de câmbio | Execução real e idempotência comprovadas (#217) | 100% |
| Seed isolado de proventos | Revisão arquitetural em curso; execução v1 suspensa (#226) | 70% |
| Rebuild pré-produção | Gates estruturais preparados; execuções reais pendentes | 97% |
| Eventos corporativos | Fundação pronta | 30% |
| IRPF | Planejado | 15% |
| Backup/Restore administrativo | Planejado (#83) | 10% |
| OAuth social | Planejado | 0% |

Prontidão global estimada para a primeira produção: **91%**. O percentual não inclui funcionalidades futuras de produto.

## Consolidado

### Contrato financeiro

- `summary.v2` e `rentabilidade.v2` estritos.
- Valuation intradiário separado de performance fechada.
- Resultado realizado, não realizado e proventos com fontes compartilhadas.
- Ausência de TWR representada por `null`.
- Cobertura, estimativa e data de referência expostas.
- Reconciliação monetária entre páginas e snapshots.

### Tesouro Direto

- Catálogo canônico persistido.
- RendA+ e Educa+ normalizados pelo ano comercial.
- Fonte primária de preço recente, fallback oficial e último preço persistido.
- Resolução case-insensitive de ticker e alias.
- Preço associado ao ticker original da posição.
- Criação automática de ativos duplicados bloqueada.
- Valores atuais validados na interface.
- Contrato `pre-prod-treasury-seed.v1` implementado com identidade operacional, baseline, cobertura e integridade.
- Advisory lock, transação única, commit final e rollback integral coordenados pela CLI `pre_prod_treasury_seed`.
- `run_id`, branch `stable-15jun` e SHA completo são validados antes da abertura das sessões.
- Contrato `pre-prod-treasury-seed-idempotency.v1` e CLI offline implementados para comparar duas evidências sem acesso a banco ou rede.
- Wrapper `scripts/Invoke-PreProdTreasuryIdempotency.ps1` implementado para coordenar as duas execuções, preservar artefatos e comparar usando caminhos host/container reconciliados.
- Execução real e comprovação operacional de idempotência permanecem pendentes na Issue #208.

### Benchmarks macroeconômicos

- Contrato `pre-prod-macro-seed.v1` implementado para CDI, SELIC, IPCA e IGPM.
- CLI, advisory lock, sessão transacional externa, commit único e rollback integral implementados.
- Wrapper `scripts/pre_prod_macro_seed.ps1` preserva a evidência por `run_id`.
- Comparador `pre-prod-macro-seed-compare.v1` aceita UTF-8 com ou sem BOM e mede novas linhas pelo delta real da tabela.
- Execuções `20260725-231557` e `20260725-231604`, no commit `181597c21f9769896cd7bc74dfdae929f2a0b3c0`, comprovaram estado final estável, zero novas linhas, zero duplicidades e zero indicadores não suportados.
- Wrapper `scripts/compare_pre_prod_macro_seed.ps1` persiste a prova offline sem sobrescrever artefatos existentes.
- Câmbio e proventos permanecem separados deste estágio por fronteira arquitetural.

### Câmbio

- Contrato `pre-prod-fx-seed.v1` implementado para `USD-BRL`, fonte `BCB` e tipo `PTAX_SELL`.
- Inspeção read-only, cliente PTAX estrito, preparação com `commit=False`, advisory lock, transação única e CLI auditável implementados.
- A CLI exige `run_id`, branch `stable-15jun`, SHA completo e intervalo inicial/final antes de abrir sessões.
- Respostas vazias, datas duplicadas, linhas fora da janela e pares não suportados são bloqueantes.
- `docs/pre-prod-fx-seed-runbook.md` documenta o ensaio controlado e a segunda execução idempotente.
- A opção OData `$orderby` foi removida após resposta HTTP 400 do endpoint oficial; a ordenação e a seleção do boletim mais recente permanecem no parser local.
- Execuções `20260728-103750` e `20260728-104238`, no commit `37c1d800be6f21dfc5c91b332a6ebe8748c0ac1c`, comprovaram estado final estável em 6 linhas, zero crescimento na segunda execução, zero duplicidades, zero pares não suportados e `ok=true`.
- A Issue #217 foi encerrada como concluída.

### Proventos — estágio isolado

- Issue dedicada #226 criada e vinculada às Issues #158 e #216.
- Contrato canônico `pre-prod-dividends-seed.v2` publicado em `docs/PRE_PROD_DIVIDENDS_SEED_CONTRACT.md`.
- Decisão canônica revisada: eventos pertencem exclusivamente ao ativo e `asset_dividends` é a única fonte de verdade.
- A coleta futura lerá o catálogo de ativos e escreverá somente em `asset_dividends`; carteiras e transações não participam da identidade nem da persistência do evento.
- Direitos por carteira serão calculados sob consulta a partir de `asset_dividends` e do histórico de posições.
- Consumidores, portas de escrita e modelos ORM de `dividends` foram removidos;
  a contração física está preparada e aguarda a janela controlada da #158.
- Transação única, advisory lock, rollback integral, fontes explícitas e comparador offline são gates obrigatórios.
- O estágio permanece isolado de B3, Tesouro, benchmarks, câmbio, importação, posições, snapshots e `full_market_rebuild`.
- Coletor BRAPI/Yahoo estrito e sequencial, persistência global exclusiva em
  `asset_dividends`, inspeções canônicas e CLI transacional implementados.
- Comparador offline e wrapper `scripts/Invoke-PreProdDividendsIdempotency.ps1` preservam as três evidências sem acesso a banco ou rede durante a comparação.
- `docs/pre-prod-dividends-seed-runbook.md` define pré-condições, comando oficial, critérios de sucesso/aborto e registro das evidências.
- Suíte específica e integral aprovadas no SHA operacional; duas execuções reais controladas permanecem pendentes.

### Histórico e snapshots

- B3 COTAHIST como histórico primário de renda variável brasileira.
- Histórico oficial do Tesouro persistido.
- `PortfolioSnapshot` e `PortfolioClassSnapshot` materializados.
- Backfills idempotentes.
- Cobertura parcial e retorno estimado explícitos.

## Atualização BRAPI Pro e eventos corporativos — 31/07/2026

- Cliente v2 com catálogo, resolução, renomes, coverage e erros tipados concluído.
- Auditoria real do plano Pro executada para a janela 2000–hoje, sem escrita no banco.
- Desdobramento e grupamento confirmados em `stockDividends` e normalizados pelo `label`.
- BRAPI definida como fonte primária; equivalências exatas do Yahoo são deduplicadas.
- Catálogo `corporate_events` em migração compatível para identidade e proveniência
  independentes de provedor, ativo de destino, datas completas e revisão.
- Reconciliação persistente e carga histórica controlada implementadas; aplicação
  real permanece condicionada à migration, backup e janela autorizada.
- Projeção canônica integrada à carteira, snapshots, direitos de proventos e
  Bens e Direitos do IRPF, sempre com gate `MATCHED` + `VALIDATED`.
- P&L realizado por ativo e snapshots TWR por classe integrados ao mesmo gate;
  eventos corporativos não são tratados como fluxos externos.
- Adaptador legado de performance migrado para a posição canônica, sem alterar o
  contrato público de resposta.
- Scheduler incremental e observabilidade implementados com feature flag segura;
  ativação depende da migration e dos gates do runbook.
- API de revisão administrativa implementada com SuperAdmin, justificativa,
  resolução de conflitos e trilha de auditoria imutável para ciclos automáticos.
- Interface administrativa integrada ao Painel Admin com filtros, paginação,
  confirmação de decisão e atualização da fila/auditoria.
- Comparação detalhada de evidências concluída, com campos econômicos lado a
  lado, divergências destacadas e payload bruto por provedor.
- Modelagem econômica de eventos complexos concluída para subscrição, mudança
  de ticker, conversão, incorporação, fusão, cisão, amortização e deslistagem,
  com termos obrigatórios e bloqueio de aprovação incompleta.
- Resolução segura do ativo de destino concluída por identidade local de ID,
  ticker e ISIN, com bloqueio de conflito, ausência e ambiguidade.
- Plano não executável de troca/cisão concluído para quantidades e componentes
  em dinheiro, sem alterar posições ou inventar alocação de custo.
- Alocação explícita de base de custo, liquidação de frações e classificação do
  caixa concluídas no contrato canônico e no plano somente leitura.
- Endpoint SuperAdmin de prévia econômica concluído, sem escrita em posições.
- Simulador econômico visual concluído no Painel Admin, exclusivamente read-only.
- Contrato idempotente da futura execução concluído com gates ordenados e feature
  flag `CORPORATE_COMPLEX_EVENTS_EXECUTION_ENABLED=false`.
- Próximo gate: ledger transacional de execução e dry-run persistente, sem ativar
  escrita em posições até validação operacional dedicada.

## Em desenvolvimento

### Pré-produção — Issues #158, #199, #208, #216 e #226

- [x] Inventário read-only `pre-prod-inventory.v2` validado.
- [x] Política integral: 11 tabelas preservadas, 3 exportáveis e 10 reconstruíveis.
- [x] Backup `pre-prod-backup.v3` e restauração isolada reconciliados.
- [x] Dry-run `pre-prod-cleanup-impact.v2` aprovado sem bloqueios, ciclos ou escritas.
- [x] Exportação `pre-prod-export.v1` reconciliada.
- [x] Plano `pre-prod-cleanup-execution.v1` validado sem acesso ao banco.
- [x] Executor transacional, CLI e artefatos auditáveis implementados.
- [x] Captura automática de baseline, pós-contagem e tabelas preservadas.
- [x] Cenário de sucesso `20260723-213000` reconciliado.
- [x] Cenário de rollback `20260723-213001` reconciliado.
- [x] PR #198 promovida para a `main`; Issue #196 encerrada.
- [x] Issue operacional exclusiva #199 criada e ativa.
- [x] Nova cadeia `20260724-100752` validada sem escrita.
- [x] Autorização humana explícita registrada na Issue #199.
- [x] Bloqueio arquitetural da CLI isolada identificado antes da primeira escrita.
- [x] Perfil `sgi-pre-prod-real` implementado sem duplicar o executor.
- [x] Perfil real validado com 34 testes e `compileall` sem erros.
- [x] Perfil real promovido para a `main` pela PR #204.
- [x] Wrapper PowerShell oficial criado para a execução real controlada.
- [x] Entry point isolado B3/COTAHIST implementado.
- [x] Contrato, inspeção, advisory lock e orquestração transacional do Tesouro implementados.
- [x] Histórico oficial do Tesouro refatorado para sessão externa e `commit=False`.
- [x] CLI `pre_prod_treasury_seed` e runbook dedicado implementados.
- [x] Identidade operacional (`run_id`, branch e SHA) implementada, validada e promovida pela PR #210.
- [x] Contrato e CLI offline de idempotência implementados na PR #211.
- [x] Wrapper operacional da prova de idempotência implementado na PR #212.
- [x] Contrato, inspeção, serviço, CLI e wrapper do seed de benchmarks implementados.
- [x] Duas execuções reais de benchmarks preservadas e comparadas.
- [x] Idempotência de benchmarks comprovada com `ok=true`.
- [x] Persistidor da comparação e runbook de benchmarks implementados.
- [x] Contrato, inspeção, cliente PTAX estrito, preparação, orquestração e CLI do seed cambial implementados.
- [x] Runbook do seed cambial implementado e documentação viva sincronizada.
- [x] Seed isolado de câmbio executado e reconciliado.
- [x] Idempotência cambial comprovada em segunda execução no mesmo SHA e intervalo.
- [x] Issue #217 encerrada após evidência real.
- [x] Issue #226 criada para o seed isolado de proventos.
- [x] Contrato canônico `pre-prod-dividends-seed.v2` e fronteiras operacionais publicados.
- [x] Envelope, inspeções, coleta estrita e persistência global exclusiva implementados.
- [x] CLI transacional, comparador offline, wrapper PowerShell e runbook de proventos publicados.
- [x] Executar a suíte integral da implementação v1 no SHA então aprovado.
- [x] Suspender a execução v1 e formalizar `asset_dividends` como fonte canônica única.
- [x] Migrar consumidores para o cálculo derivado por posição histórica.
- [x] Desativar portas de escrita por carteira e remover os modelos ORM legados.
- [x] Preparar migration física protegida para `dividends` e
  `dividends_sync_jobs`, sem executá-la.
- [ ] Realizar duas execuções reais controladas e reconciliar as três evidências.
- [ ] Gerar nova cadeia operacional vinculada ao SHA promovido.
- [ ] Recalcular e revisar a confirmação composta.
- [ ] Executar limpeza real somente após nova autorização explícita.
- [ ] Reconciliar imediatamente `committed=true` e `reconciliation.ok=true`.
- [ ] Executar e reconciliar o seed isolado B3 COTAHIST.
- [ ] Executar e reconciliar o seed isolado do Tesouro.
- [ ] Comprovar idempotência do Tesouro em segunda execução controlada usando o wrapper oficial.
- [ ] Inventariar e implementar o estágio isolado de proventos.
- [ ] Importação CSV completa da carteira.
- [ ] Rebuild de posições e snapshots.
- [ ] Auditoria de cobertura e reconciliação final.

### Rentabilidade

- [ ] Implementar TWR dedicado para Tesouro e Renda Fixa (#149).
- [ ] Materializar histórico persistido do IBOV (#150).
- [ ] Remover serviço legado de rentabilidade (#151).

### Segurança e dívida técnica

- [ ] Endurecer ou remover o router administrativo de debug antes do go-live.
- [ ] Migrar timestamps UTC para timezone-aware (#192).
- [ ] Revisar backup/restore administrativo (#83).

### Dependabot — #159

- [x] Auditoria concluída e Issue #159 encerrada.
- [x] Atualizações compatíveis integradas em blocos isolados.
- [x] TypeScript 7 revertido para 6.0.3 após incompatibilidade com `typescript-eslint@8.64.0` (#182).
- [x] Nenhuma PR Dependabot aberta no fechamento deste bloco.

## Próximas prioridades

1. Gerar nova cadeia operacional vinculada ao SHA promovido.
2. Executar e reconciliar a limpeza real pela Issue #199.
3. Executar e reconciliar B3 e Tesouro em estágios independentes.
4. Concluir a migração canônica de Proventos e redesenhar os gates antes de qualquer nova execução controlada.
5. Executar importação e rebuild em blocos independentes.
6. Endurecer ou remover o router administrativo de debug antes do go-live.
7. Remover o serviço legado de rentabilidade (#151).
8. Materializar IBOV (#150).
9. Implementar TWR dedicado para Tesouro e Renda Fixa (#149).
10. Migrar timestamps UTC para timezone-aware (#192).

## Backlog

- Eventos corporativos — #129.
- Evolução da integração de dados de mercado — #130.
- Backup/Restore administrativo — #83.
- Google OAuth — #97.
- IRPF — #56.
- Análise de Carteira — #57.
- Janela Global do Ativo — #58.
- Provedores configuráveis — #127.
- UX da página Patrimônio — #90.

## Processo

1. Desenvolvimento na `stable-15jun`.
2. Commits pequenos e isolados.
3. Validação em ambiente de desenvolvimento.
4. Atualização contínua de Issues, README, ROADMAP, CHANGELOG e documentação técnica.
5. PR da `stable-15jun` para `main` ao fechar bloco estrutural.
