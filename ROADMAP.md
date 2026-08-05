# Roadmap modular — SGI v2

> Última atualização: 05/08/2026

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
| Rentabilidade | Consolidação canônica concluída | 100% |
| IRPF | Implementação funcional canônica concluída; validação real pendente | 98% |
| Metas | Estável e vinculada à carteira | 100% |
| Rotas de carteira | Consolidadas | 100% |
| UTC e warnings | Concluído pela #192 | 100% |
| Pré-produção e rebuild | Suspenso pelo gate #227 | 85% |
| Eventos corporativos | Bootstrap canônico estruturado; certificação pendente | 88% |
| IBOV persistido | Planejado | 20% |
| TWR dedicado Tesouro/Renda Fixa | Planejado | 20% |

## Qualidade validada

- Backend: `1246 passed`, `22 skipped` na suíte completa mais recente, executada duas vezes após a remoção física do serviço legado de Rentabilidade.
- `compileall`, Flake8 e build Docker do backend: aprovados.
- Frontend: 26 arquivos de teste, 93 testes, typecheck, lint e build aprovados.

## Consolidado

### Núcleo financeiro

- Contratos `summary.v2` e `rentabilidade.v2` permanecem as fontes públicas canônicas.
- Projeções compartilhadas calculam posição, custo e resultado realizado.
- A fachada `rentabilidade_service.py` foi removida; nenhum consumidor de produção ou teste pode reintroduzir esse módulo sem falhar no gate arquitetural.
- A invalidação das chaves `rent:*` está isolada em `rentabilidade_cache_service.py` e é consumida pelos fluxos de transação, importação CSV e reconstrução de snapshots.
- O IRPF usa contratos públicos versionados para apuração anual, Bens e Direitos, Rendimentos e Ganhos de Capital.
- Day Trade, Swing Trade, isenção mensal, compensação de prejuízos, IRRF e DARF mínima estão integrados ao motor canônico.
- PDF e CSV são gerados diretamente por `IrpfCanonicalExport`, sem leitura do relatório persistido legado.
- A `IRPFPage.tsx` usa somente hooks canônicos; `IRPFReportOut` permanece apenas na fachada Python histórica e no endpoint completo de compatibilidade externa.
- Proventos pertencem ao ativo e são persistidos em `asset_dividends`; direitos de carteira são derivados sob demanda.
- O contrato operacional vigente de seed de Proventos é `pre-prod-dividends-seed.v2`, com escrita exclusiva em `asset_dividends` e sem materialização por carteira.
- Serviços operacionais usam UTC aware; defaults ORM `timezone=False` usam UTC naive explícito.

### Bootstrap canônico de ativos

- O pipeline neutro possui capacidades independentes para catálogo, preços, Proventos, eventos corporativos e cobertura.
- Dependências, duplicidades, ordem inválida e ciclos são validados antes da execução.
- Cada etapa expõe estado `planned`, `executed`, `blocked` ou `failed`.
- Planejamento e execução aceitam identidade auditável por `run_id`, branch e commit SHA.
- A CLI `plan_asset_bootstrap` produz envelope versionado read-only, sem importar fixtures de teste, providers, ORM ou sessões de banco.
- Comparadores offline detectam alterações entre planos de backfill e relatórios do bootstrap.
- Nenhuma capacidade produtiva de provider ou persistência real foi conectada enquanto a Issue #227 permanecer bloqueante.

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

- [x] Backend verde e sem regressões conhecidas.
- [x] Frontend verde e com build aprovado.
- [x] IRPF e Metas sob `/carteira`.
- [x] README, ROADMAP, CHANGELOG e documentação técnica sincronizados para o IRPF canônico.
- [ ] Abrir e validar a PR `stable-15jun` → `main`.

### 2. IRPF

- [x] Caracterizar Day Trade e Swing Trade.
- [x] Caracterizar isenção mensal e prejuízos acumulados.
- [x] Caracterizar segregação mensal, retenções e DARF mínima.
- [x] Integrar reconstrução contábil com leitores/projeções canônicos.
- [x] Publicar contratos versionados e migrar frontend/exportações.
- [ ] Validar PDF, CSV e apuração com carteira real representativa quando houver dados homologados.
- [ ] Avaliar remoção física do endpoint completo legado após auditoria externa de consumidores.

### 3. Rentabilidade

- [x] Migrar consumidores restantes de posição/custo/PnL.
- [x] Isolar invalidação de cache em serviço canônico.
- [x] Remover a fachada e caches legados sem uso.
- [x] Manter regressões arquiteturais contra cálculos paralelos e reintrodução do módulo.

### 4. Eventos corporativos

- [x] Inventariar e classificar o legado em fluxos read-only.
- [x] Estruturar bootstrap canônico por capacidades neutras.
- [x] Adicionar planejamento, cobertura, dependências e identidade auditável.
- [ ] Executar suíte focada e corrigir regressões locais.
- [ ] Certificar migrations e idempotência sintética.
- [ ] Consolidar consumidores restantes do motor canônico (#129).
- [ ] Evoluir adapters sem expor payloads de fornecedor ao domínio (#130).
- [ ] Consolidar registry por capacidade (#127).

### 5. Performance e benchmarks

- [ ] Materializar histórico persistido do IBOV (#150).
- [ ] Implementar TWR dedicado para Tesouro e Renda Fixa (#149).

### 6. Retomada operacional

Somente após os gates anteriores:

- [ ] Executar duas rodadas reais do contrato `pre-prod-dividends-seed.v2` (#226).
- [ ] Reconciliar #158 e #216.
- [ ] Importar CSV real.
- [ ] Reconstruir posições e snapshots.
- [ ] Executar auditoria financeira final.

## Próximas prioridades

1. Executar a suíte focada do bootstrap canônico e corrigir regressões.
2. Certificar eventos corporativos, migrations e idempotência sintética.
3. Sincronizar documentação final e abrir a PR estrutural `stable-15jun` → `main`.
4. Implementar IBOV persistido e TWR dedicado.
5. Retomar pré-produção somente após a certificação da #227.
6. Validar o IRPF em carteira real quando houver dados representativos.
