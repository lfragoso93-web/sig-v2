# Roadmap modular — SGI v2

> Última atualização: 17/07/2026

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
| Proventos | Em validação final | 92% |
| Página Resumo | Em refinamento funcional | 95% |
| Página Patrimônio | Auditoria concluída, regressão visual mapeada | 90% |
| Página Rentabilidade | Contratos concluídos | 95% |
| Dependências | Auditoria parcial, pendências mapeadas | 80% |
| Rebuild pré-produção | Planejado e bloqueador do go-live | 10% |
| Eventos corporativos | Fundação pronta | 30% |
| IRPF | Planejado | 15% |
| Backup/Restore | Planejado | 10% |
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
- BRAPI como fonte primária de preço recente.
- Tesouro Transparente como fallback oficial.
- Último preço persistido como contingência.
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

### Página Resumo

- [ ] Revisar KPIs atuais e sinal de retorno negativo.
- [ ] Garantir distinção entre variação diária e rentabilidade acumulada.
- [ ] Revisar dropdowns e overflow das tabelas.
- [ ] Padronizar cards com a página Patrimônio.
- [ ] Corrigir visual do gráfico divergente (#147).

### Proventos

- [x] Eventos canônicos e materialização por carteira.
- [x] Totais financeiros usando eventos líquidos recebidos.
- [ ] Validar cobertura completa por classe.
- [ ] Melhorar diagnóstico de eventos não materializados.
- [ ] Validar seed de ativos de renda variável.
- [ ] Implementar tooltip mensal por classe (#131).

### Patrimônio e Rentabilidade

- [ ] Restaurar gráficos históricos por classe (#148).
- [ ] Implementar TWR dedicado para Tesouro e Renda Fixa (#149).
- [ ] Materializar histórico persistido do IBOV (#150).
- [ ] Remover serviço legado de rentabilidade (#151).

### Dependabot — #159

Integrado e validado na `stable-15jun`:

- [x] react-hook-form 7.81.0.
- [x] Recharts 3.9.2.
- [x] aiosqlite 0.22.1.
- [x] Uvicorn 0.51.0.
- [x] redis-py 8.0.1.

Pendente de validação isolada:

- [ ] #146 — build-tools, incluindo TypeScript 7.0.2.
- [ ] #138 — ESLint e typescript-eslint.
- [ ] #137 — httpx 0.28.1.
- [ ] #133 — mypy 2.2.0.

### Pré-produção — #158

- [ ] Backup e teste de restauração.
- [ ] Dry-run da limpeza.
- [ ] Limpeza de dados reconstruíveis.
- [ ] Seed B3 COTAHIST.
- [ ] Seed Tesouro Transparente.
- [ ] Seed de benchmarks e proventos.
- [ ] Importação CSV completa da carteira.
- [ ] Rebuild de posições e snapshots.
- [ ] Auditoria de cobertura e reconciliação final.

## Próximas prioridades

1. Refinar Página Resumo.
2. Concluir validação funcional de Proventos.
3. Restaurar históricos por classe em Patrimônio (#148).
4. Implementar TWR dedicado de Tesouro e Renda Fixa (#149).
5. Materializar IBOV (#150).
6. Remover rentabilidade legada (#151).
7. Validar Dependabot pendente (#159).
8. Executar rebuild limpo antes do go-live (#158).

## Backlog

- Eventos corporativos — #129.
- Evolução da integração BRAPI — #130.
- Backup/Restore — #83.
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
