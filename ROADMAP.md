# Roadmap modular — SGI v2

> Última atualização: 24/07/2026

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
| Backup/Restore pré-produção | Validação real v3 concluída (#183) | 100% |
| Dry-run de limpeza | Validado no PostgreSQL real (#185) | 100% |
| Exportação pré-produção | Validada e promovida pela PR #191 (#188) | 100% |
| Planejamento seguro da limpeza | Validado pela Issue #195 e PR #194 | 100% |
| Limpeza isolada | Sucesso e rollback reconciliados; PR #198 promovida | 100% |
| Rebuild pré-produção | Ensaio isolado aprovado; limpeza real ainda não autorizada | 90% |
| Eventos corporativos | Fundação pronta | 30% |
| IRPF | Planejado | 15% |
| Backup/Restore administrativo | Planejado (#83) | 10% |
| OAuth social | Planejado | 0% |

Prontidão global estimada para a primeira produção: **88%**. O percentual não inclui funcionalidades futuras de produto.

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

### Histórico e snapshots

- B3 COTAHIST como histórico primário de renda variável brasileira.
- Histórico oficial do Tesouro persistido.
- `PortfolioSnapshot` e `PortfolioClassSnapshot` materializados.
- Backfills idempotentes.
- Cobertura parcial e retorno estimado explícitos.

## Em desenvolvimento

### Pré-produção — Issue #158

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
- [ ] Criar e aprovar Issue operacional exclusiva para a limpeza da pré-produção real.
- [ ] Gerar novo backup imediatamente anterior à janela de execução.
- [ ] Gerar nova exportação e novo plano com o mesmo `run_id` operacional.
- [ ] Executar limpeza real somente após autorização explícita.
- [ ] Seed B3 COTAHIST.
- [ ] Seed oficial do Tesouro Direto.
- [ ] Seed de benchmarks, câmbio e proventos.
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
- [ ] Arquivar ou remover migration órfã do Tesouro após confirmação de uso externo.

### Dependabot — #159

- [x] Auditoria concluída e Issue #159 encerrada.
- [x] Atualizações compatíveis integradas em blocos isolados.
- [x] TypeScript 7 revertido para 6.0.3 após incompatibilidade com `typescript-eslint@8.64.0` (#182).
- [x] Nenhuma PR Dependabot aberta após a promoção da PR #198.

## Próximas prioridades

1. Criar e revisar a Issue de autorização da limpeza na pré-produção real.
2. Atualizar a Issue-mãe #158 com o estado concluído até o ensaio isolado.
3. Endurecer ou remover o router administrativo de debug antes do go-live.
4. Remover o serviço legado de rentabilidade (#151).
5. Materializar IBOV (#150).
6. Implementar TWR dedicado para Tesouro e Renda Fixa (#149).
7. Migrar timestamps UTC para timezone-aware (#192).

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
