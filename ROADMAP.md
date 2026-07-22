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
| Configuração Pydantic v2 | Migração ampliada após validação local; nova suíte pendente (#186) | 95% |
| Rebuild pré-produção | Backup/restore, dry-run e exportação validados | 80% |
| Backup/Restore pré-produção | Validação real v3 concluída (#183) | 100% |
| Dry-run de limpeza | Validado no PostgreSQL real (#185) | 100% |
| Exportação pré-produção | Validada e promovida pela PR #191 (#188) | 100% |
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
- [x] Nenhuma PR Dependabot aberta após o merge da PR #191.

### Pydantic v2 — #186

- [x] Migrar `Settings` para `SettingsConfigDict`.
- [x] Migrar schemas de portfólio e auditoria inicialmente identificados.
- [x] Adicionar inventário AST que bloqueia novas `class Config`.
- [x] Incorporar os quatro pontos adicionais revelados pela validação local: ativos, proventos, Tesouro e `AssetListItem`.
- [x] Adicionar regressões de leitura por atributos para os schemas adicionais.
- [ ] Reexecutar a suíte com `PydanticDeprecatedSince20` tratado como erro.
- [ ] Encerrar a Issue após zero warnings e ausência de regressões.

### Pré-produção — #158 / #176 / #183 / #185 / #188

- [x] Inventário read-only `pre-prod-inventory.v2` validado no PostgreSQL real.
- [x] Política integral: 11 tabelas preservadas, 3 exportáveis e 10 reconstruíveis.
- [x] Backup `pre-prod-backup.v3` e restauração isolada reconciliados.
- [x] Dry-run `pre-prod-cleanup-impact.v2` aprovado, sem bloqueios, ciclos ou escritas.
- [x] Exportação `pre-prod-export.v1` das tabelas `corporate_events`, `fixed_income_investments` e `transactions`.
- [x] Execução real `20260722-134741`: 3 tabelas, 323 linhas, 47.576 bytes, `reconciled=true` e exit code `0`.
- [x] Incompatibilidade de `ordinal_position` do PostgreSQL corrigida e protegida por regressão.
- [x] Issue #188 encerrada e PR #191 promovida para a `main`.
- [ ] Implementar contrato e serviço de limpeza controlada.
- [ ] Executar limpeza das tabelas reconstruíveis com gate aprovado.
- [ ] Seed B3 COTAHIST.
- [ ] Seed oficial do Tesouro Direto.
- [ ] Seed de benchmarks, câmbio e proventos.
- [ ] Importação CSV completa da carteira.
- [ ] Rebuild de posições e snapshots.
- [ ] Auditoria de cobertura e reconciliação final.

## Próximas prioridades

1. Revalidar e encerrar a migração Pydantic v2 (#186).
2. Implementar o contrato e o serviço de limpeza controlada da #158, sem executar escrita real neste primeiro sub-bloco.
3. Executar a limpeza e o rebuild pré-produção em etapas auditáveis.
4. Remover o serviço legado de rentabilidade (#151).
5. Materializar IBOV (#150).
6. Implementar TWR dedicado, separando Tesouro e Renda Fixa (#149).

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
4. Atualização contínua de Issues, README, ROADMAP, CHANGELOG e documentação técnica.
5. PR da `stable-15jun` para `main` ao fechar bloco estrutural.
