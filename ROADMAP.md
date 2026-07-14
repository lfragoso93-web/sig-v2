# Roadmap modular — SGI v2

> Última atualização: 14/07/2026

Este roadmap organiza o SGI v2 por módulos de produto e arquitetura.

---

## Visão geral

| Módulo | Status | Progresso |
|---|---|---:|
| Core backend e autenticação | Estável | 100% |
| Carteiras e transações | Estável | 100% |
| Importação CSV | Estável com melhorias contínuas | 95% |
| Dados canônicos | Em validação | 95% |
| Histórico de preços | Em validação | 95% |
| Gap sync e smart sync | Em validação | 95% |
| Snapshots TWR | Em validação | 90% |
| Proventos | Em validação | 85% |
| Tesouro Direto | Em validação | 80% |
| Rentabilidade | Backend pronto, UI pendente | 85% |
| Página Resumo | Revisão pendente | 60% |
| Dashboard | Evolução pendente | 45% |
| Eventos corporativos | Fundação pronta | 25% |
| IRPF | Planejado | 15% |
| Backup/Restore | Planejado | 10% |
| OAuth social | Planejado | 0% |

---

## ✅ Concluído ou consolidado

### Core

- Backend FastAPI assíncrono.
- PostgreSQL, Redis, Alembic e Docker Compose.
- Login JWT, refresh token e administração de usuários.
- Carteiras isoladas por usuário.
- Exclusão segura com preservação de auditoria.

### Importação CSV

- Preview e `dry_run`.
- Validação linha a linha.
- Bloqueio de importação quando há erro impeditivo.
- Resolução temporal de tickers antigos.
- Rebuild automático de dados financeiros após importação.

### Dados canônicos

- KPIs compartilhados entre páginas.
- Resultado financeiro separado de rentabilidade.
- Proventos materializados por carteira.
- TWR diário e acumulado persistido nos snapshots.

### Histórico de preços

- Auditoria de cobertura por ativo.
- Gap sync por lacuna.
- Smart sync com status de provedor.
- Validação de preços inválidos.
- Histórico máximo quando suportado.
- Sessões curtas durante chamadas externas.

### Full market rebuild

- Comando oficial `python -m app.cli.full_market_rebuild`.
- Orquestração de catálogo, preços, Tesouro, benchmarks, proventos, snapshots e auditoria final.
- Propagação de erros internos para o status geral.

---

## 🚧 Em desenvolvimento

### Rentabilidade

- [x] Backend TWR para Hoje, Mês, 12 meses e Desde o início.
- [x] Composição mensal correta.
- [x] Resultado financeiro incluindo proventos.
- [ ] Ajustar cards visuais para a nova semântica.
- [ ] Exibir `has_partial_prices` e `return_is_estimated`.

### Resumo

- [x] Base canônica de patrimônio, investido e resultado.
- [ ] Revalidar todos os cards após TWR e materialização de proventos.
- [ ] Conferir divergências entre Resumo e Patrimônio.
- [ ] Ajustar variação diária vs rentabilidade acumulada.
- [ ] Revisar dropdowns e overflow em tabelas.

### Tesouro Direto

- [x] Catálogo dedicado.
- [x] Preços atuais dedicados.
- [x] Histórico dedicado em `asset_prices`.
- [x] Remoção do pipeline genérico de gap sync.
- [ ] Fazer snapshots consumirem o histórico dedicado sem cair em preço médio.
- [ ] Completar validação de histórico por título.

### Proventos

- [x] Eventos canônicos.
- [x] Materialização por carteira.
- [x] Processamento em lotes seguros.
- [ ] Revisar cobertura por classe.
- [ ] Melhorar diagnóstico quando eventos existem, mas não materializam.
- [ ] Validar impacto total no Resultado e TWR.

### Provedores e roteamento

- [x] Metadados persistentes no ativo.
- [x] `provider_symbol`.
- [x] `provider_status`.
- [x] Histórico máximo para lacunas iniciais suportadas.
- [ ] Provider router definitivo por capacidade.
- [ ] Roteamento definitivo de cripto.
- [ ] Fallback por falhas recorrentes.
- [ ] Uso em lote no histórico quando a rota suportar múltiplos símbolos.

### Mercado fracionário

- [x] Normalização de `provider_symbol` para ticker-base.
- [ ] Evitar duplicação física de histórico usando referência canônica de preço.
- [ ] Ajustar leitura de preço por `pricing_asset_id` ou alias equivalente.

---

## Próximas prioridades

1. Finalizar consumo de Tesouro no snapshot.
2. Resolver preço canônico para mercado fracionário.
3. Revalidar `full_market_rebuild` após as últimas otimizações.
4. Ajustar visualmente Rentabilidade.
5. Revisar cards da página Resumo.
6. Abrir PR única de `stable-15jun` para `main` quando a arquitetura estiver validada.

---

## Backlog

### Eventos corporativos

- Splits.
- Grupamentos.
- Bonificações.
- Incorporações.
- Fusões.
- Conversões complexas.
- Simulação e rollback.

### Backup/Restore

- Backup autenticado para download.
- Checksum.
- Lock de operação.
- Auditoria.
- Restore em ambiente isolado.

### IRPF

- Ano-calendário.
- Isenção mensal.
- Swing trade e day trade.
- DARF e relatórios.

### Janela global do ativo

- Histórico de preços.
- Histórico de proventos.
- Posição consolidada.
- Resultado por ativo.
- Eventos corporativos.

### Provedores configuráveis

- Registry/factory por capacidade.
- Configuração via Superadmin.
- Credenciais criptografadas.
- Health check por provedor.
- Rollback de configuração.

---

## Processo

1. Desenvolvimento na `stable-15jun`.
2. Commits pequenos e isolados.
3. Validação com Docker e `full_market_rebuild`.
4. Atualização de README, roadmap e changelog.
5. PR única para `main` ao fechar bloco estrutural.
