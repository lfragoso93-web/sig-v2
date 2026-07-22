# Roadmap modular — SGI v2

> Última atualização: 22/07/2026

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
| Rebuild pré-produção | Backup/restore, dry-run e exportação validados | 80% |
| Backup/Restore pré-produção | Validação real v3 concluída (#183) | 100% |
| Dry-run de limpeza | Validado no PostgreSQL real (#185) | 100% |
| Exportação pré-produção | Validada no PostgreSQL real (#188) | 100% |
| Eventos corporativos | Fundação pronta | 30% |
| IRPF | Planejado | 15% |
| Backup/Restore administrativo | Planejado (#83) | 10% |
| OAuth social | Planejado | 0% |

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

A reconstrução limpa do catálogo, históricos e carteira ficou reservada para o checklist pré-produção (#158).

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
- [x] Nenhuma PR Dependabot aberta após o merge da PR #184.

### Pré-produção — #158 / #176 / #183 / #185 / #188

- [x] Runbook operacional com classificação de dados e critérios de abortar.
- [x] Serviço read-only de inventário com contrato `pre-prod-inventory.v2`.
- [x] CLI `python -m app.cli.pre_prod_inventory` com saída UTF-8.
- [x] Testes que bloqueiam verbos SQL de escrita durante o inventário.
- [x] Inventário executado no PostgreSQL real: 24 tabelas e zero inconsistências canônicas.
- [x] Política completa para tabelas preservadas, exportáveis e reconstruíveis; nenhuma tabela conhecida permanece sem classificação.
- [x] Issue #176 concluída após validação integral do inventário v2.
- [x] CLI de backup v3 com pg_dump PostgreSQL 16, paridade de major, snapshot único com o inventário, listagem, SHA-256 e manifesto por execução.
- [x] CLI de restauração com checksum, destino vazio/diferente e transação única.
- [x] Inventário v2 da restauração e reconciliação de migrations, tabelas, contagens e achados.
- [x] Confirmar aborto seguro da tentativa v1 incompatível, sem escrita na origem.
- [x] Restaurar o backup v2 no banco isolado e diagnosticar divergência temporal de 998 linhas em `asset_prices`, sem escrita na origem.
- [x] Reexecutar backup/restore v3 no PostgreSQL real: snapshot consistente, reconciliação `ok=true` e zero escritas na origem.
- [x] Encerrar a Issue #183 e promover a PR #184 para a `main`.
- [x] Implementar contrato `pre-prod-cleanup-impact.v2`, DAG reutilizável, introspecção de foreign keys, serviço e CLI read-only (#185).
- [x] Validar 45 testes relacionados, sem falhas; avisos Pydantic rastreados separadamente na Issue #186.
- [x] Executar o dry-run no PostgreSQL real: 24 tabelas, 4.673.320 linhas, 11 preservadas, 3 exportáveis, 10 reconstruíveis, zero bloqueios, zero ciclos e zero escritas.
- [x] Persistir o artefato `artifacts/pre-prod-rebuild/20260722-101848/cleanup-impact.json` com `ok=true` e exit code `0`.
- [x] Implementar contrato `pre-prod-export.v1`, serviço, CLI e runbook de exportação auditável (#188).
- [x] Compartilhar o mesmo snapshot `REPEATABLE READ READ ONLY` entre gate de impacto e exportação.
- [x] Exportar `corporate_events`, `fixed_income_investments` e `transactions` com SHA-256 de dados e schema, sem sobrescrita.
- [x] Normalizar ordinais do artefato CSV para preservar contrato contíguo mesmo após colunas removidas no PostgreSQL.
- [x] Executar a exportação real `20260722-134741`: 3 tabelas, 323 linhas, 47.576 bytes, `reconciled=true`, exit code `0` e zero escritas.
- [ ] Limpeza de dados reconstruíveis.
- [ ] Seed B3 COTAHIST.
- [ ] Seed oficial do Tesouro Direto.
- [ ] Seed de benchmarks e proventos.
- [ ] Importação CSV completa da carteira.
- [ ] Rebuild de posições e snapshots.
- [ ] Auditoria de cobertura e reconciliação final.

## Próximas prioridades

1. Promover a conclusão estrutural da Issue #188 para a `main` pela PR #191.
2. Implementar a limpeza controlada das tabelas reconstruíveis no escopo da #158, usando o gate e os artefatos já validados.
3. Implementar TWR dedicado de Tesouro e Renda Fixa (#149).
4. Materializar IBOV (#150).
5. Remover rentabilidade legada (#151).

## Backlog

- Migração das configurações Pydantic v2 para `ConfigDict` — #186.
- Eventos corporativos — #129.
- Evolução da integração de dados de mercado — #130.
- Backup/Restore administrativo — #83.
- Google OAuth — #97.
- IRPF — #56.
- Análise de Carteira — #57.
- Janela Global do Ativo — #58.
- Provedores configuráveis — #127.

## Processo

1. Desenvolvimento na `stable-15jun`.
2. Commits pequenos e isolados.
3. Validação em ambiente de desenvolvimento.
4. Atualização de issues, README, ROADMAP e CHANGELOG.
5. PR da `stable-15jun` para `main` ao fechar bloco estrutural.
