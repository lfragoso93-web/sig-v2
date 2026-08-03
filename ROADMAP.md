# Roadmap modular — SGI v2

> Última atualização: 02/08/2026

## Direção atual

O SGI v2 está em consolidação arquitetural antes de receber carteiras e usuários reais. Até o encerramento da Issue #227, novas cargas reais, seeds externos e rebuilds permanecem opt-in e bloqueados por gates explícitos.

## Estado por módulo

| Módulo | Status | Progresso |
|---|---|---:|
| Core backend e autenticação | Estável | 100% |
| Carteiras e transações | Estável | 100% |
| Dados canônicos e DB-first | Consolidado | 100% |
| Histórico B3 / Tesouro / benchmarks / câmbio | Consolidado | 100% |
| Proventos canônicos | Implementação concluída; execução real pendente | 95% |
| Snapshots e valuation por classe | Consolidado | 100% |
| Resumo e Patrimônio | Consolidado | 100% |
| Rentabilidade | Migração canônica em andamento | 96% |
| IRPF — Bens e Direitos | Canônico | 100% |
| IRPF — ganhos mensais | Caracterização pendente | 45% |
| Metas | Estável e vinculada à carteira | 100% |
| Rotas de carteira | Consolidadas | 100% |
| UTC e warnings | Concluído pela #192 | 100% |
| Pré-produção e rebuild | Suspenso pelo gate #227 | 85% |
| Eventos corporativos | Motor canônico implementado | 75% |
| IBOV persistido | Planejado | 20% |
| TWR dedicado Tesouro/Renda Fixa | Planejado | 20% |

## Qualidade validada

- Backend: `1097 passed`, `22 skipped`, zero warnings.
- Ruff e `compileall`: aprovados.
- Frontend: 23 arquivos de teste, 86 testes, typecheck, lint e build aprovados.

## Consolidado

### Núcleo financeiro

- Contratos `summary.v2` e `rentabilidade.v2` permanecem as fontes públicas canônicas.
- Projeções compartilhadas calculam posição, custo e resultado realizado.
- Bens e Direitos do IRPF consome posição histórica na data de corte.
- Regras fiscais, relatório e exportação do IRPF estão separados por responsabilidade.
- Proventos pertencem ao ativo e são persistidos em `asset_dividends`; direitos de carteira são derivados sob demanda.
- Serviços operacionais usam UTC aware; defaults ORM `timezone=False` usam UTC naive explícito.

### Navegação por carteira

Rotas canônicas:

- `/carteira`;
- `/carteira/patrimonio`;
- `/carteira/rentabilidade`;
- `/carteira/transacoes`;
- `/carteira/proventos`;
- `/carteira/metas`;
- `/carteira/irpf`;
- `/carteira/configuracoes`.

`/metas` e `/irpf` permanecem apenas como redirects temporários.

## Blocos em execução

### 1. Promoção estrutural

- [x] Backend verde e sem warnings.
- [x] Frontend verde e com build aprovado.
- [x] IRPF e Metas sob `/carteira`.
- [x] Issues #192 e #228 encerradas.
- [x] README e documentação de continuidade atualizados.
- [ ] Sincronizar documentação restante e abrir PR para `main`.

### 2. Ganhos de capital do IRPF

- [ ] Caracterizar Day Trade e Swing Trade.
- [ ] Caracterizar isenção mensal e prejuízos acumulados.
- [ ] Caracterizar segregação mensal e retenções.
- [ ] Migrar reconstrução contábil para leitores canônicos.
- [ ] Preservar somente semântica fiscal no módulo IRPF.

### 3. Rentabilidade

- [ ] Migrar consumidores restantes de posição/custo/PnL.
- [ ] Remover a fachada e caches legados quando ficarem sem uso.
- [ ] Manter regressões arquiteturais contra cálculos paralelos.

### 4. Eventos corporativos

- [ ] Consolidar consumidores restantes do motor canônico (#129).
- [ ] Evoluir adapters sem expor payloads de fornecedor ao domínio (#130).
- [ ] Consolidar registry por capacidade (#127).

### 5. Performance e benchmarks

- [ ] Materializar histórico persistido do IBOV (#150).
- [ ] Implementar TWR dedicado para Tesouro e Renda Fixa (#149).

### 6. Retomada operacional

Somente após os gates anteriores:

- [ ] Executar duas rodadas reais do seed de Proventos v2 (#226).
- [ ] Reconciliar #158 e #216.
- [ ] Importar CSV real.
- [ ] Reconstruir posições e snapshots.
- [ ] Executar auditoria financeira final.

## Próximas prioridades

1. Abrir e validar a PR estrutural `stable-15jun` → `main`.
2. Caracterizar ganhos de capital mensais do IRPF.
3. Concluir a migração da Rentabilidade e remover legado (#151).
4. Consolidar eventos corporativos e adapters.
5. Implementar IBOV persistido e TWR dedicado.
6. Retomar pré-produção somente após a certificação da #227.
