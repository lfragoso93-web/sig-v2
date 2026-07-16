# Roadmap modular — SGI v2

> Última atualização: 16/07/2026

Este roadmap organiza o SGI v2 por módulos de produto e arquitetura.

## Visão geral

| Módulo | Status | Progresso |
|---|---|---:|
| Core backend e autenticação | Estável | 100% |
| Carteiras e transações | Estável | 100% |
| Importação CSV | Estável | 95% |
| Dados canônicos | Consolidado | 100% |
| Histórico B3 COTAHIST | Consolidado | 100% |
| Tesouro Direto | Consolidado | 100% |
| Renda Fixa | Consolidado | 100% |
| Snapshots TWR | Consolidado | 100% |
| Proventos | Em validação final | 90% |
| Rentabilidade | Backend consolidado, UI pendente | 90% |
| Página Resumo | Auditoria pendente | 70% |
| Eventos corporativos | Fundação pronta | 30% |
| IRPF | Planejado | 15% |
| Backup/Restore | Planejado | 10% |
| OAuth social | Planejado | 0% |

## Concluído ou consolidado

### Dados canônicos e snapshots

- KPIs compartilhados entre Resumo, Patrimônio e Rentabilidade.
- Resultado financeiro separado da rentabilidade percentual.
- Proventos materializados por carteira.
- TWR diário e acumulado persistido nos snapshots.
- Valuation dedicado para mercado, Tesouro e Renda Fixa.
- `has_partial_prices` e `return_is_estimated` derivados da cobertura real.

### Histórico de mercado brasileiro

- B3 COTAHIST como fonte histórica oficial.
- Carga idempotente para ações, FIIs, ETFs nacionais e BDRs.
- 2.258 ativos e 984.949 preços carregados no primeiro rebuild validado.
- Preservação de ativos deslistados.
- Pré-listagem separada de lacuna real.
- Gap sync mantido apenas para complementos recentes e contingência.

### Tesouro Direto

- Catalog v2 orientado pelo Tesouro Transparente.
- Histórico oficial persistido em `asset_prices`.
- Brapi apenas como fallback.
- Aliases legados auditados e deduplicados.
- RendA+ e Educa+ normalizados pelo ano comercial.
- Snapshots consumindo histórico oficial: `treasury_matched=3`, `treasury_unresolved=0` na carteira validada.

### Renda Fixa

- Contratos reconstruídos por aplicações e resgates.
- Valuation por regras e indexadores dedicados.
- Classe removida do lookup genérico de mercado.
- Diagnóstico de principal, valor corrigido e rendimento no rebuild.

### Full market rebuild

- Comando oficial `python -m app.cli.full_market_rebuild`.
- Orquestração de catálogo, preços, Tesouro, benchmarks, proventos, snapshots e auditoria.
- Serviços auxiliares para catálogo do Tesouro e histórico B3.
- Execuções idempotentes e diagnósticos estruturados.

## Em desenvolvimento

### Resumo

- [ ] Auditar Patrimônio, Investido, Resultado e Rentabilidade contra o último snapshot canônico.
- [ ] Confirmar Resultado incluindo todos os proventos materializados.
- [ ] Conferir divergências entre Resumo e Patrimônio.
- [ ] Validar sinais negativos e períodos desde o início.
- [ ] Criar testes de contrato dos cards.

### Rentabilidade

- [x] Backend TWR para Hoje, Mês, 12 meses e Desde o início.
- [x] Qualidade real por snapshot.
- [ ] Ajustar cards visuais e textos.
- [ ] Exibir indicadores de cobertura quando necessário.

### Proventos

- [x] Eventos canônicos e materialização por carteira.
- [x] Processamento em lotes seguros.
- [ ] Validar cobertura por classe.
- [ ] Melhorar diagnósticos de eventos não materializados.
- [ ] Confirmar impacto total no Resultado e TWR durante a auditoria dos cards.

### B3 Historical Market Rebuild

- [x] Leitura em lote por arquivo anual.
- [x] Persistência idempotente.
- [x] Ciclo de vida de negociação.
- [ ] Integrar a carga anual ao `full_market_rebuild` após validação operacional final.
- [ ] Definir política automática para download do ano corrente.

### Motor de eventos corporativos — #129

- [x] Fundação de aliases e `TICKER_CHANGE`.
- [ ] Splits, grupamentos e bonificações.
- [ ] Simulação, confirmação e rollback.
- [ ] Administração e auditoria operacional.

## Próximas prioridades

1. Auditoria dos cards da página Resumo.
2. Validação final de Resultado + proventos + TWR.
3. Integração operacional do COTAHIST ao rebuild completo.
4. Ajustes visuais de Rentabilidade.
5. Evolução do motor de eventos corporativos.
6. Backup/Restore, OAuth, IRPF e Janela Global do Ativo.

## Backlog

- Backup/Restore — #83.
- Google OAuth — #97.
- IRPF — #56.
- Análise de Carteira — #57.
- Janela Global do Ativo — #58.
- Provedores configuráveis — #127.

## Processo

1. Desenvolvimento na `stable-15jun`.
2. Commits pequenos e isolados.
3. Validação com Docker e comandos operacionais.
4. Atualização de README, roadmap e changelog.
5. PR única para `main` ao fechar bloco estrutural.
