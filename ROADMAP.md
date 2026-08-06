# Roadmap modular — SGI v2

> Última atualização: 06/08/2026

## Direção atual

O SGI v2 está em consolidação arquitetural antes de receber carteiras e usuários reais. Até o encerramento da Issue #227, novas cargas reais, seeds externos e rebuilds permanecem opt-in e bloqueados por gates explícitos.

## Estado por módulo

| Módulo | Status | Progresso |
|---|---|---:|
| Core backend e autenticação | Estável | 100% |
| Carteiras e transações | Estável | 100% |
| Dados canônicos e DB-first | Consolidado | 100% |
| Histórico B3 / Tesouro / benchmarks / câmbio | Consolidado; consumidor atual de USD/BRL ainda não DB-first | 95% |
| Proventos canônicos | Implementação concluída; execução real pendente | 95% |
| Snapshots e valuation por classe | Consolidado | 100% |
| Resumo e Patrimônio | Consolidado | 100% |
| Rentabilidade | Consolidação canônica promovida à `main` | 100% |
| IRPF | Implementação canônica promovida; validação real pendente | 98% |
| Metas | Contrato `goals` estável; schema legado `goal_allocations` sob decisão | 98% |
| Rotas de carteira | Consolidadas | 100% |
| UTC e warnings | Concluído pela #192 | 100% |
| Pré-produção e rebuild | Suspenso pelo gate #227 | 85% |
| Eventos corporativos | Bootstrap canônico validado parcialmente; consumidores e convergência de schema pendentes | 90% |
| Convergência Alembic/ORM | Inventário e gates concluídos; correções por domínio pendentes | 25% |
| IBOV persistido | Planejado | 20% |
| TWR dedicado Tesouro/Renda Fixa | Planejado | 20% |

## Qualidade validada

- Backend IRPF: `1265 passed`, `22 skipped` na suíte completa promovida pela PR #237.
- Backend Rentabilidade: `1246 passed`, `22 skipped` em duas execuções completas promovidas pela PR #240.
- Gates Alembic/ORM: 16 testes focados aprovados no HEAD `bcf2fe66deace7210caccb845d44921f47ff4fa5`.
- `compileall`, Flake8, Ruff e build Docker: aprovados nos macroblocos promovidos.
- Frontend: 26 arquivos de teste, 93 testes, typecheck, lint e build aprovados.

## Consolidado

### Núcleo financeiro

- Contratos `summary.v2` e `rentabilidade.v2` permanecem as fontes públicas canônicas.
- Projeções compartilhadas calculam posição, custo e resultado realizado.
- A fachada `rentabilidade_service.py` foi removida e promovida à `main` pela PR #240.
- A invalidação das chaves `rent:*` está isolada em `rentabilidade_cache_service.py`.
- O IRPF canônico foi promovido à `main` pela PR #237.
- Proventos pertencem ao ativo e são persistidos em `asset_dividends`; direitos de carteira são derivados sob demanda.
- Serviços operacionais usam UTC aware; defaults ORM `timezone=False` usam UTC naive explícito.

### Bootstrap canônico de ativos

- O pipeline neutro possui capacidades independentes para catálogo, preços, Proventos, eventos corporativos e cobertura.
- Dependências, duplicidades, ordem inválida e ciclos são validados antes da execução.
- Cada etapa expõe estado `planned`, `executed`, `blocked` ou `failed`.
- Planejamento e execução aceitam identidade auditável por `run_id`, branch e commit SHA.
- A CLI `plan_asset_bootstrap` produz envelope versionado read-only.
- Comparadores offline detectam alterações entre planos e relatórios.
- PostgreSQL vazio alcança o head `20260731_corp_event_catalog` e a reexecução de `upgrade head` é idempotente.
- `alembic check` permanece bloqueado pela deriva global rastreada na #241.

### Câmbio e metas

- A série de câmbio persistida e o seed PTAX estão consolidados.
- O endpoint `/usd-brl` ainda consulta BRAPI durante request e usa fallback fixo; a migração para leitura DB-first é prioridade imediata.
- O fluxo atual de metas usa somente `goals` por carteira e KPIs canônicos.
- `goal_allocations` não possui consumidor runtime comprovado e permanece preservado até fixture sintética e decisão explícita.

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

- [x] Backend verde e sem regressões conhecidas nos macroblocos promovidos.
- [x] Frontend verde e com build aprovado.
- [x] IRPF promovido pela PR #237.
- [x] Rentabilidade promovida pela PR #240.
- [x] `main` reintegrada à `stable-15jun` sem divergência após as promoções.
- [ ] Promover o próximo macrobloco somente após fechar o gate Alembic/ORM e certificar eventos corporativos.

### 2. IRPF

- [x] Motor canônico e contratos versionados.
- [x] Frontend e exportações migrados.
- [x] Promoção para `main` concluída.
- [ ] Validar PDF, CSV e apuração com carteira real representativa quando houver dados homologados.
- [ ] Avaliar remoção física do endpoint completo legado após auditoria externa de consumidores.

### 3. Rentabilidade

- [x] Consumidores migrados.
- [x] Invalidação de cache isolada.
- [x] Fachada legada removida.
- [x] Promoção para `main` concluída.

### 4. Eventos corporativos e Alembic

- [x] Inventariar e classificar legado em fluxos read-only.
- [x] Estruturar bootstrap canônico por capacidades neutras.
- [x] Adicionar planejamento, cobertura, dependências e identidade auditável.
- [x] Validar `upgrade head`, `current` e reexecução idempotente em PostgreSQL vazio.
- [x] Criar Issue #241, inventários e gates contra autogenerate monolítico.
- [x] Classificar `app_config`, `irpf_reports`, `fx_rates`, `goal_allocations` e tabelas fiscais legadas.
- [ ] Migrar `/usd-brl` para leitor persistido DB-first.
- [ ] Tratar modelos sem migration e tabelas migradas fora do ORM por domínio.
- [ ] Consolidar consumidores restantes do motor canônico (#129).
- [ ] Evoluir adapters sem expor payloads de fornecedor (#130).
- [ ] Consolidar registry por capacidade (#127).
- [ ] Obter `alembic check` limpo após convergência controlada.

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

1. Migrar o endpoint `/usd-brl` para leitura persistida DB-first e remover fallback fixo.
2. Continuar a convergência Alembic/ORM por contratos isolados na #241.
3. Consolidar consumidores e campos legados de eventos corporativos na #129.
4. Sincronizar documentação final e abrir a próxima PR estrutural `stable-15jun` → `main`.
5. Implementar IBOV persistido e TWR dedicado.
6. Retomar pré-produção somente após a certificação da #227.
7. Validar o IRPF em carteira real quando houver dados representativos.
