# Roadmap modular — SGI v2

> Última atualização: 21/07/2026

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
| Rebuild pré-produção | Backup/restore validados; dry-run iniciado | 65% |
| Backup/Restore pré-produção | Validação real v3 concluída (#183) | 100% |
| Dry-run de limpeza | Planejado e rastreado pela Issue #185 | 10% |
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

### Pré-produção — #158 / #176 / #183 / #185

- [x] Runbook operacional com classificação de dados e critérios de abortar.
- [x] Serviço read-only de inventário com contrato `pre-prod-inventory.v2`.
- [x] CLI `python -m app.cli.pre_prod_inventory` com saída UTF-8.
- [x] Testes que bloqueiam verbos SQL de escrita durante o inventário.
- [x] Inventário executado no PostgreSQL real: 24 tabelas, 4.671.361 registros e zero inconsistências canônicas.
- [x] Política completa para tabelas preservadas, exportáveis e reconstruíveis; nenhuma tabela conhecida permanece sem classificação.
- [x] Issue #176 concluída após validação integral do inventário v2.
- [x] CLI de backup v3 com pg_dump PostgreSQL 16, paridade de major, snapshot único com o inventário, listagem, SHA-256 e manifesto por execução.
- [x] CLI de restauração com checksum, destino vazio/diferente e transação única.
- [x] Inventário v2 da restauração e reconciliação de migrations, tabelas, contagens e achados.
- [x] Confirmar aborto seguro da tentativa v1 incompatível, sem escrita na origem.
- [x] Restaurar o backup v2 no banco isolado e diagnosticar divergência temporal de 998 linhas em `asset_prices`, sem escrita na origem.
- [x] Reexecutar backup/restore v3 no PostgreSQL real: snapshot consistente, reconciliação `ok=true` e zero escritas na origem.
- [x] Encerrar a Issue #183 e promover a PR #184 para a `main`.
- [ ] Implementar dry-run read-only da limpeza e relatório de impacto (#185).
- [ ] Executar o dry-run no PostgreSQL real e anexar evidências de zero escrita.
- [ ] Exportar dados das tabelas classificadas como exportáveis.
- [ ] Limpeza de dados reconstruíveis.
- [ ] Seed B3 COTAHIST.
- [ ] Seed oficial do Tesouro Direto.
- [ ] Seed de benchmarks e proventos.
- [ ] Importação CSV completa da carteira.
- [ ] Rebuild de posições e snapshots.
- [ ] Auditoria de cobertura e reconciliação final.

## Próximas prioridades

1. Implementar e validar o dry-run read-only da limpeza (#185).
2. Somente após encerrar #185, preparar a exportação controlada das tabelas exportáveis (#158).
3. Implementar TWR dedicado de Tesouro e Renda Fixa (#149).
4. Materializar IBOV (#150).
5. Remover rentabilidade legada (#151).

## Backlog

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
