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

### Página Resumo — #161

- [x] Mapear contratos, endpoints e divergências arquiteturais.
- [x] Revisar KPIs atuais e sinal de retorno negativo.
- [x] Garantir distinção entre variação diária e rentabilidade acumulada.
- [x] Revisar dropdowns e overflow das tabelas.
- [x] Padronizar cards com a página Patrimônio.
- [x] Corrigir e validar o gráfico divergente (#147).
- [x] Executar suítes finais, consolidar evidências e promover pela PR #164.

### Proventos — #165

- [x] Preservar as entregas funcionais das Issues #92 e #95.
- [x] Mapear arquitetura, contratos, duplicidades e riscos atuais.
- [x] Adicionar testes de caracterização antes de alterar comportamento.
- [x] Unificar contratos e filtros de resumo, lista, histórico e distribuição.
- [x] Separar leitura de materialização e centralizar elegibilidade.
- [x] Consolidar coleta e scheduler após validar consumidores.
- [x] Validar seed, coleta e materialização de ações, FIIs, ETFs e BDRs.
- [x] Revisar API, frontend, gráficos, tabelas e indicadores.
- [x] Implementar tooltip mensal por classe (#131).
- [x] Validar suítes backend/frontend e sincronizar a documentação viva.
- [x] Promover a Fase 2 para a `main` pela PR #166.

### Patrimônio — #148

- [x] Restaurar gráficos históricos consolidados e por classe.
- [x] Padronizar períodos, estados de consulta e tooltips canônicos.
- [x] Exibir cobertura parcial e retorno estimado sem cálculo paralelo.
- [x] Reconciliar consolidado × classes somente na mesma data.
- [x] Reconciliar consumidores do valuation intradiário sem comparar com o fechamento.
- [x] Remover clientes legados sem consumidores e endpoints frontend obsoletos.

### Rentabilidade

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
- [ ] Seed oficial do Tesouro Direto.
- [ ] Seed de benchmarks e proventos.
- [ ] Importação CSV completa da carteira.
- [ ] Rebuild de posições e snapshots.
- [ ] Auditoria de cobertura e reconciliação final.

## Próximas prioridades

1. Implementar TWR dedicado de Tesouro e Renda Fixa (#149).
2. Materializar IBOV (#150).
3. Remover rentabilidade legada (#151).
4. Validar Dependabot pendente (#159).
5. Executar rebuild limpo antes do go-live (#158).

## Backlog

- Eventos corporativos — #129.
- Evolução da integração de dados de mercado — #130.
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
