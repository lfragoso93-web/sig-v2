# Roadmap modular — SGI v2

> Última atualização: 23/07/2026

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
| Dependências | Auditoria concluída; nenhuma PR aberta | 100% |
| Configuração Pydantic v2 | Migração validada e Issue #186 encerrada | 100% |
| Rebuild pré-produção | Ensaio da limpeza isolada em preparação | 87% |
| Backup/Restore pré-produção | Validação real v3 concluída (#183) | 100% |
| Dry-run de limpeza | Validado no PostgreSQL real (#185) | 100% |
| Exportação pré-produção | Validada e promovida pela PR #191 (#188) | 100% |
| Planejamento seguro da limpeza | Validado pela Issue #195 e PR #194 | 100% |
| Limpeza isolada | Executor, CLI e artefato implementados; ensaio real pendente (#196 / PR #198) | 85% |
| Eventos corporativos | Fundação pronta | 30% |
| IRPF | Planejado | 15% |
| Backup/Restore administrativo | Planejado (#83) | 10% |
| OAuth social | Planejado | 0% |

Prontidão global estimada para a primeira produção: **88%**. O percentual não
inclui funcionalidades futuras de produto. Revisão e fila priorizada:
`docs/ARCHITECTURAL_REVIEW_2026-07-23.md`.

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

A reconstrução limpa do catálogo, históricos e carteira permanece reservada ao checklist pré-produção da Issue #158.

### Histórico e snapshots

- B3 COTAHIST como histórico primário de renda variável brasileira.
- Histórico oficial do Tesouro persistido.
- `PortfolioSnapshot` e `PortfolioClassSnapshot` materializados.
- Backfills idempotentes.
- Cobertura parcial e retorno estimado explícitos.

## Em desenvolvimento

### Rentabilidade

- [ ] Implementar TWR dedicado para Tesouro e Renda Fixa (#149).
- [ ] Materializar histórico persistido do IBOV (#150).
- [ ] Remover serviço legado de rentabilidade (#151).

### Dependabot — #159

- [x] Auditoria concluída e Issue #159 encerrada.
- [x] Atualizações compatíveis integradas em blocos isolados.
- [x] TypeScript 7 revertido para 6.0.3 após incompatibilidade com `typescript-eslint@8.64.0` (#182).
- [x] Build Docker do frontend confirmado pelo usuário.
- [x] Nenhuma PR Dependabot aberta após o merge da PR #194.

### Pydantic v2 — #186

- [x] Migrar `Settings` para `SettingsConfigDict`.
- [x] Migrar schemas de portfólio e auditoria inicialmente identificados.
- [x] Adicionar inventário AST que bloqueia novas `class Config`.
- [x] Incorporar os quatro pontos adicionais revelados pela validação local: ativos, proventos, Tesouro e `AssetListItem`.
- [x] Adicionar regressões de leitura por atributos para os schemas adicionais.
- [x] Confirmar a suíte dedicada com `5 passed`.
- [x] Confirmar ausência de `PydanticDeprecatedSince20` durante a coleta e execução integral.
- [x] Isolar os testes de compatibilidade das variáveis reais do container.
- [x] Tornar o teste documental compatível com a imagem isolada do backend sem enfraquecer a validação no checkout completo.
- [x] Reexecutar a suíte integral após os dois ajustes de infraestrutura de teste.
- [x] Encerrar a Issue após ausência de regressões.

Validação final: `666 passed`, `1 skipped` intencional e zero `PydanticDeprecatedSince20`.

### Pré-produção — #158 / #176 / #183 / #185 / #188 / #195 / #196

- [x] Inventário read-only `pre-prod-inventory.v2` validado no PostgreSQL real.
- [x] Política integral: 11 tabelas preservadas, 3 exportáveis e 10 reconstruíveis.
- [x] Backup `pre-prod-backup.v3` e restauração isolada reconciliados.
- [x] Dry-run `pre-prod-cleanup-impact.v2` aprovado, sem bloqueios, ciclos ou escritas.
- [x] Exportação `pre-prod-export.v1` das tabelas `corporate_events`, `fixed_income_investments` e `transactions`.
- [x] Execução real `20260722-134741`: 3 tabelas, 323 linhas, 47.576 bytes, `reconciled=true` e exit code `0`.
- [x] Incompatibilidade de `ordinal_position` do PostgreSQL corrigida e protegida por regressão.
- [x] Issue #188 encerrada e PR #191 promovida para a `main`.
- [x] Contrato `pre-prod-cleanup-execution.v1` e CLI `pre_prod_cleanup_plan` implementados.
- [x] Checksums, identidade operacional, gate, DAG, publicação atômica e rollback de exportação cobertos.
- [x] PR #194 promovida para a `main` com 33 testes focados aprovados.
- [x] Cadeia real de exportação + plano validada sem escrita no banco pela Issue #195.
- [x] Issue #196 aberta para a execução controlada em banco isolado.
- [x] Executor transacional com lock, contagens, ordem canônica, pós-condições e rollback integral implementado.
- [x] CLI `pre_prod_isolated_cleanup` e relatórios `committed`, `aborted` e `rolled_back` implementados.
- [x] Validação multiplataforma concluída com 44 testes aprovados e `compileall` sem erros.
- [x] Runbook D0 do ensaio isolado concluído com gates, comandos PowerShell, reconciliação e descarte.
- [ ] Implementar captura automática de baseline e pós-execução das tabelas preservadas.
- [ ] Executar cenário de sucesso em PostgreSQL descartável restaurado do backup v3.
- [ ] Executar e reconciliar cenário de rollback em nova restauração e novo `run_id`.
- [ ] Promover a PR #198 para a `main` após o bloco estrutural validado.
- [ ] Avaliar autorização separada para limpeza da pré-produção real somente após o ensaio aprovado.
- [ ] Seed B3 COTAHIST.
- [ ] Seed oficial do Tesouro Direto.
- [ ] Seed de benchmarks, câmbio e proventos.
- [ ] Importação CSV completa da carteira.
- [ ] Rebuild de posições e snapshots.
- [ ] Auditoria de cobertura e reconciliação final.

## Próximas prioridades

1. Implementar captura automática e reconciliação das tabelas preservadas para o ensaio da Issue #196.
2. Executar os cenários de sucesso e rollback somente em banco PostgreSQL descartável.
3. Promover a PR #198 após validação integral do ensaio isolado.
4. Executar limpeza e rebuild pré-produção apenas após nova autorização explícita.
5. Remover o serviço legado de rentabilidade (#151).
6. Materializar IBOV (#150).
7. Implementar TWR dedicado, separando Tesouro Direto e Renda Fixa (#149).
8. Migrar timestamps UTC para timezone-aware (#192).

## Backlog

- Eventos corporativos — #129.
- Evolução da integração de dados de mercado — #130.
- Backup/Restore administrativo — #83.
- Google OAuth — #97.
- IRPF — #56.
- Análise de Carteira — #57.
- Janela Global do Ativo — #58.
- Provedores configuráveis — #127.
- Timestamps UTC timezone-aware — #192.

## Processo

1. Desenvolvimento na `stable-15jun`.
2. Commits pequenos e isolados.
3. Validação em ambiente de desenvolvimento.
4. Atualização contínua de Issues, README, ROADMAP, CHANGELOG e documentação técnica.
5. PR da `stable-15jun` para `main` ao fechar bloco estrutural.
