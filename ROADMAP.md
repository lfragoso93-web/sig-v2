# Roadmap modular — SGI v2

> Última atualização: 20/07/2026

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
| Página Patrimônio | Fase 3 concluída na `stable-15jun`; promoção pendente | 100% |
| Página Rentabilidade | Contratos concluídos | 95% |
| Dependências | Auditoria concluída; incompatibilidade TS7 corrigida | 100% |
| Rebuild pré-produção | Backup/restore implementados; validação real pendente | 55% |
| Backup/Restore pré-produção | CLIs e reconciliação implementados (#183) | 80% |
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

### Pré-produção — #158 / #176 / #183

- [x] Runbook operacional com classificação de dados e critérios de abortar.
- [x] Serviço read-only de inventário com contrato `pre-prod-inventory.v2`.
- [x] CLI `python -m app.cli.pre_prod_inventory` com saída UTF-8.
- [x] Testes que bloqueiam verbos SQL de escrita durante o inventário.
- [x] Inventário executado no PostgreSQL real: 24 tabelas, 4.671.361 registros e zero inconsistências canônicas.
- [x] Política completa para tabelas preservadas, exportáveis e reconstruíveis; nenhuma tabela conhecida permanece sem classificação.
- [x] Issue #176 concluída após validação integral do inventário v2.
- [x] CLI de backup com pg_dump custom, listagem, SHA-256 e manifesto por execução.
- [x] CLI de restauração com checksum, destino vazio/diferente e transação única.
- [x] Inventário v2 da restauração e reconciliação de migrations, tabelas, contagens e achados.
- [ ] Executar backup/restore no PostgreSQL real e anexar a reconciliação aprovada à Issue #183.
- [ ] Dry-run da limpeza com relatório de impacto.
- [ ] Limpeza de dados reconstruíveis.
- [ ] Seed B3 COTAHIST.
- [ ] Seed oficial do Tesouro Direto.
- [ ] Seed de benchmarks e proventos.
- [ ] Importação CSV completa da carteira.
- [ ] Rebuild de posições e snapshots.
- [ ] Auditoria de cobertura e reconciliação final.

## Próximas prioridades

1. Executar e validar o ciclo real de backup/restauração isolada (#183).
2. Somente após encerrar #183, preparar o dry-run de limpeza (#158).
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
