# Roadmap modular — SGI v2

> Última atualização: 25/07/2026

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
| Dependências | Auditoria concluída; nenhuma PR aberta no início da Issue #199 | 100% |
| Configuração Pydantic v2 | Migração validada e Issue #186 encerrada | 100% |
| Backup/Restore pré-produção | Validação real v3 concluída (#183) | 100% |
| Dry-run de limpeza | Validado no PostgreSQL real (#185) | 100% |
| Exportação pré-produção | Validada e promovida pela PR #191 (#188) | 100% |
| Planejamento seguro da limpeza | Validado pela Issue #195 e PR #194 | 100% |
| Limpeza isolada | Sucesso e rollback reconciliados; PR #198 promovida | 100% |
| Perfil de alvo real | Implementado, validado e promovido pela PR #204 | 100% |
| Seed isolado B3/COTAHIST | Entry point implementado; execução pendente | 90% |
| Seed isolado Tesouro | Identidade e comparador de idempotência implementados; execução real pendente (#208) | 95% |
| Rebuild pré-produção | Gates estruturais preparados; execuções reais pendentes | 94% |
| Eventos corporativos | Fundação pronta | 30% |
| IRPF | Planejado | 15% |
| Backup/Restore administrativo | Planejado (#83) | 10% |
| OAuth social | Planejado | 0% |

Prontidão global estimada para a primeira produção: **89%**. O percentual não inclui funcionalidades futuras de produto.

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
- Execução real e comprovação operacional de idempotência permanecem pendentes na Issue #208.

### Histórico e snapshots

- B3 COTAHIST como histórico primário de renda variável brasileira.
- Histórico oficial do Tesouro persistido.
- `PortfolioSnapshot` e `PortfolioClassSnapshot` materializados.
- Backfills idempotentes.
- Cobertura parcial e retorno estimado explícitos.

## Em desenvolvimento

### Pré-produção — Issues #158, #199 e #208

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
- [ ] Gerar nova cadeia operacional vinculada ao SHA promovido.
- [ ] Recalcular e revisar a confirmação composta.
- [ ] Executar limpeza real somente após nova autorização explícita.
- [ ] Reconciliar imediatamente `committed=true` e `reconciliation.ok=true`.
- [ ] Executar e reconciliar o seed isolado B3 COTAHIST.
- [ ] Executar e reconciliar o seed isolado do Tesouro.
- [ ] Comprovar idempotência do Tesouro em segunda execução controlada usando o comparador offline.
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

### Dependabot — #159

- [x] Auditoria concluída e Issue #159 encerrada.
- [x] Atualizações compatíveis integradas em blocos isolados.
- [x] TypeScript 7 revertido para 6.0.3 após incompatibilidade com `typescript-eslint@8.64.0` (#182).
- [x] Nenhuma PR Dependabot aberta no início da Issue #199.

## Próximas prioridades

1. Validar e promover a PR #211 com o comparador de idempotência do Tesouro.
2. Gerar nova cadeia operacional vinculada ao SHA promovido.
3. Executar e reconciliar a limpeza real pela Issue #199.
4. Executar e reconciliar B3 e Tesouro em estágios independentes.
5. Comprovar idempotência e atualizar a Issue #158 antes dos próximos seeds.
6. Executar benchmarks, câmbio, proventos, importação e rebuild em blocos independentes.
7. Endurecer ou remover o router administrativo de debug antes do go-live.
8. Remover o serviço legado de rentabilidade (#151).
9. Materializar IBOV (#150).
10. Implementar TWR dedicado para Tesouro e Renda Fixa (#149).
11. Migrar timestamps UTC para timezone-aware (#192).

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
