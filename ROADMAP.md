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
| Tesouro Direto — valuation | Consolidado | 100% |
| Renda Fixa — valuation | Consolidado | 100% |
| Snapshots TWR consolidados | Consolidado | 100% |
| Snapshots TWR por classe de mercado | Consolidado | 100% |
| Proventos | Em validação final | 92% |
| Página Resumo | Auditoria concluída | 95% |
| Página Patrimônio | Auditoria concluída, regressão visual mapeada | 90% |
| Página Rentabilidade | Auditoria e contratos concluídos | 95% |
| Eventos corporativos | Fundação pronta | 30% |
| IRPF | Planejado | 15% |
| Backup/Restore | Planejado | 10% |
| OAuth social | Planejado | 0% |

## Concluído ou consolidado

### Contrato financeiro e páginas principais

- Contrato financeiro oficial documentado em `docs/CANONICAL_FINANCIAL_CONTRACT.md`.
- `summary.v2` e `rentabilidade.v2` validados em runtime com campos extras proibidos.
- Patrimônio, custo, resultado realizado, resultado não realizado e proventos usam fontes compartilhadas.
- Valuation intradiário separado de performance fechada.
- Ausência de TWR representada por `null`, sem falso `0%`.
- Metadados de cobertura, estimativa, fonte e data de referência expostos.
- Reconciliação monetária entre Resumo, Patrimônio, Rentabilidade e snapshots.

### Resumo

- KPIs auditados contra valuation, snapshots e proventos canônicos.
- Histórico mensal baseado no último snapshot de cada mês.
- “Todo período” sem corte artificial.
- Tabela de posições com variação diária separada de resultado acumulado.
- Proventos por classe/ticker usando somente eventos líquidos recebidos.
- Pendência visual do gráfico divergente registrada na issue #147.

### Patrimônio

- Cards alinhados à semântica financeira canônica.
- Evolução diária e mensal usando custo das posições abertas.
- Aportes e retiradas preservados como fluxo externo separado.
- Distribuição por classe consumida do endpoint canônico.
- Regressão dos gráficos históricos por classe registrada na issue #148.

### Rentabilidade

- KPIs monetários derivados de `summary.v2`.
- TWR diário, mensal, 12 meses e desde o início derivado dos snapshots.
- TWR por classe materializado para ações, FIIs, ETFs, BDRs, stocks e cripto.
- Tesouro e Renda Fixa exibem valuation e resultado atuais com TWR explicitamente indisponível.
- CDI e IPCA servidos do banco; nenhuma consulta externa é feita pelo navegador.
- Resultado por ativo derivado de posições e PnL realizado canônicos.
- Endpoint de reconciliação com tolerância monetária de R$ 0,01.

### Dados canônicos e snapshots

- Valuation dedicado para mercado, Tesouro e Renda Fixa.
- `PortfolioSnapshot` para o consolidado.
- `PortfolioClassSnapshot` para classes suportadas.
- TWR diário e acumulado persistido.
- `has_partial_prices` e `return_is_estimated` derivados da cobertura real.
- Backfill consolidado e por classe integrado à manutenção noturna.

### Histórico de mercado brasileiro

- B3 COTAHIST como fonte histórica oficial.
- Carga idempotente para ações, FIIs, ETFs nacionais e BDRs.
- 2.258 ativos e 984.949 preços carregados no primeiro rebuild validado.
- Preservação de ativos deslistados.
- Pré-listagem separada de lacuna real.

### Tesouro Direto e Renda Fixa

- Tesouro com catálogo e histórico oficiais persistidos.
- Renda Fixa reconstruída por aplicação, indexador e resgate.
- Ambas removidas do lookup genérico de mercado.
- TWR diário dedicado pendente na issue #149.

### Benchmarks

- CDI composto a partir das taxas diárias persistidas.
- IPCA mensal lido de `rate_history`.
- IBOV permanece indisponível até materialização da série persistida (#150).

### Full market rebuild

- Comando oficial `python -m app.cli.full_market_rebuild`.
- Orquestração de catálogo, preços, Tesouro, benchmarks, proventos, snapshots e auditoria.
- Execuções idempotentes e diagnósticos estruturados.

## Em desenvolvimento

### Proventos

- [x] Eventos canônicos e materialização por carteira.
- [x] Processamento em lotes seguros.
- [x] Totais financeiros usando apenas eventos recebidos líquidos.
- [ ] Validar cobertura completa por classe.
- [ ] Melhorar diagnósticos de eventos não materializados.

### Pendências da auditoria funcional

- [ ] #147 — corrigir perda abaixo do zero no gráfico de evolução patrimonial.
- [ ] #148 — restaurar gráficos históricos por classe na página Patrimônio.
- [ ] #149 — implementar TWR diário dedicado para Tesouro e Renda Fixa.
- [ ] #150 — materializar histórico persistido do IBOV.
- [ ] #151 — remover serviço legado de rentabilidade e caches obsoletos.

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

1. Restaurar gráficos históricos por classe na página Patrimônio (#148).
2. Implementar TWR dedicado para Tesouro e Renda Fixa (#149).
3. Materializar o benchmark IBOV (#150).
4. Remover definitivamente o serviço legado de rentabilidade (#151).
5. Corrigir o gráfico divergente da página Resumo (#147).
6. Concluir validação funcional do módulo Proventos.
7. Evoluir eventos corporativos, Backup/Restore, OAuth, IRPF e Janela Global do Ativo.

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
3. Validação com Docker, Render e comandos operacionais.
4. Atualização de README, roadmap e changelog.
5. PR única para `main` ao fechar bloco estrutural.
