# Roadmap modular — SGI v2

> Última atualização: 07/08/2026

## Direção atual

O SGI v2 está em estabilização arquitetural final antes da próxima grande fase funcional. Até o encerramento da Issue #227, novas cargas reais, seeds externos e rebuilds permanecem opt-in e bloqueados por gates explícitos.

A Issue #241 convergiu Alembic ↔ MetaData para todos os domínios estabilizados. O único diff remanescente é `goals`, tratado deliberadamente fora do escopo porque Metas será redesenhado em conjunto com Análise de Carteira nas Issues #246 e #57.

## Estado por módulo

| Módulo | Status | Progresso |
|---|---|---:|
| Core backend e autenticação | Estável | 100% |
| Carteiras e transações | Consolidado | 100% |
| Dados canônicos e DB-first | Consolidado | 100% |
| Histórico B3 / Tesouro / benchmarks / câmbio | Consolidado | 100% |
| Proventos canônicos | Implementação concluída; execução real pendente | 95% |
| Snapshots e valuation por classe | Consolidado | 100% |
| Resumo e Patrimônio | Consolidado | 100% |
| Rentabilidade | Consolidação canônica promovida à `main` | 100% |
| IRPF | Implementação canônica promovida; validação real pendente | 98% |
| Metas | Redesenho arquitetural pendente com Análise de Carteira | 35% |
| Análise de Carteira | Planejada; será redesenhada junto com Metas | 20% |
| Rotas de carteira | Consolidadas | 100% |
| UTC e warnings | Concluído pela #192 | 100% |
| Pré-produção e rebuild | Suspenso pelo gate #227 | 85% |
| Eventos corporativos | Núcleo canônico consolidado; auditoria final de consumidores pendente | 95% |
| Convergência Alembic/ORM | Concluída fora de `goals`; exceção formalizada | 98% |
| IBOV persistido | Planejado | 20% |
| TWR dedicado Tesouro/Renda Fixa | Planejado | 20% |

## Qualidade validada

- Build Docker aprovado no HEAD `17beeb9e6ae70f51d523e273bebda368872f81de`.
- `compileall` aprovado.
- Suíte estrutural final: 15 testes aprovados.
- `app.main` importado integralmente.
- Gates contra consumidores legados e deriva Alembic/ORM aprovados.
- Backend e frontend completos permaneceram verdes nos macroblocos já promovidos.

## Consolidado

### Núcleo financeiro

- Contratos `summary.v2` e `rentabilidade.v2` permanecem as fontes públicas canônicas.
- Projeções compartilhadas calculam posição, custo e resultado realizado.
- A fachada `rentabilidade_service.py` foi removida e promovida à `main` pela PR #240.
- A invalidação das chaves `rent:*` está isolada em `rentabilidade_cache_service.py`.
- O IRPF canônico foi promovido à `main` pela PR #237.
- Proventos pertencem ao ativo e são persistidos em `asset_dividends`; direitos de carteira são derivados sob demanda.
- Transactions, snapshots, ativos, Proventos e eventos corporativos refletem o schema físico migrado.
- Serviços operacionais usam UTC aware; defaults ORM `timezone=False` usam UTC naive explícito.

### Bootstrap canônico de ativos

- O pipeline neutro possui capacidades independentes para catálogo, preços, Proventos, eventos corporativos e cobertura.
- Dependências, duplicidades, ordem inválida e ciclos são validados antes da execução.
- Cada etapa expõe estado `planned`, `executed`, `blocked` ou `failed`.
- Planejamento e execução aceitam identidade auditável por `run_id`, branch e commit SHA.
- A CLI `plan_asset_bootstrap` produz envelope versionado read-only.
- Comparadores offline detectam alterações entre planos e relatórios.
- PostgreSQL vazio alcança o head canônico e a reexecução de `upgrade head` é idempotente.

### Câmbio

- A série persistida `fx_rates` e o seed PTAX estão consolidados.
- O endpoint `/usd-brl` lê exclusivamente a última linha persistida de `fx_rates`, sem provider durante request e sem fallback fixo.
- `FxRate` participa de `Base.metadata` e representa as constraints e índices físicos canônicos.
- A ausência de cobertura cambial é retornada explicitamente como indisponibilidade.

### Metas e Análise de Carteira

- O módulo `goals` não é considerado contrato canônico estabilizado neste momento.
- Schema histórico, ORM, schemas Pydantic e service divergem em taxonomia e semântica.
- Nenhuma migration será criada apenas para limpar o `alembic check`.
- O redesenho funcional e estrutural está rastreado pela #246 e deve evoluir em conjunto com a #57.
- `goal_allocations` legado já foi tratado separadamente; a futura arquitetura deve evitar duplicação com `portfolio_class_targets`.

### Navegação por carteira

Rotas atuais:

- `/carteira`;
- `/carteira/patrimonio`;
- `/carteira/rentabilidade`;
- `/carteira/transacoes`;
- `/carteira/proventos`;
- `/carteira/metas`;
- `/carteira/irpf`;
- `/carteira/configuracoes`.

A existência da rota de Metas não implica estabilidade do contrato de domínio; ela permanece sujeita ao redesenho #246/#57. `/metas` e `/irpf` continuam como redirects temporários.

## Blocos em execução

### 1. Promoção estrutural

- [x] Backend verde e sem regressões conhecidas nos macroblocos promovidos.
- [x] Frontend verde e com build aprovado.
- [x] IRPF promovido pela PR #237.
- [x] Rentabilidade promovida pela PR #240.
- [x] `main` reintegrada à `stable-15jun` sem divergência para trás.
- [ ] Encerrar formalmente #241 e sincronizar toda a documentação final.
- [ ] Auditar arquitetura, serviços, endpoints e legado remanescente.
- [ ] Abrir PR estrutural `stable-15jun` → `main` após a certificação final.

### 2. IRPF

- [x] Motor canônico e contratos versionados.
- [x] Frontend e exportações migrados.
- [x] Consumers e persistência `IRPFReport` legados removidos.
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
- [x] Classificar e tratar `app_config`, `irpf_reports`, `fx_rates`, `goal_allocations` e tabelas fiscais legadas.
- [x] Migrar `/usd-brl` para leitor persistido DB-first e alinhar `fx_rates` no MetaData.
- [x] Alinhar por domínio ativos, Proventos, eventos corporativos, transactions, Renda Fixa, posições, snapshots, usuários, portfólios e configurações.
- [x] Formalizar `goals` como exceção arquitetural consciente, delegada à #246/#57.
- [ ] Fechar #241 após sincronização documental e registro da certificação final.
- [ ] Auditar consumidores restantes do motor canônico (#129).
- [ ] Evoluir adapters sem expor payloads de fornecedor (#130).
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

### 7. Macroprojeto Metas + Análise de Carteira

Somente após a estabilização definitiva da base:

- [ ] Definir contrato de domínio conjunto (#246 + #57).
- [ ] Decidir taxonomia de metas e relação com `portfolio_class_targets`.
- [ ] Definir KPIs calculados versus valores persistidos.
- [ ] Redesenhar schema/ORM/API/frontend sem preservar dívida apenas por compatibilidade histórica.
- [ ] Criar migrations pequenas, defensivas e reversíveis apenas após o desenho estar aprovado.

## Próximas prioridades

1. Encerrar formalmente #241 sem tocar em `goals`.
2. Fazer auditoria arquitetural global de legado, serviços e endpoints após a convergência.
3. Sincronizar documentação final e abrir a PR estrutural `stable-15jun` → `main`.
4. Consolidar eventuais consumidores restantes de eventos corporativos (#129/#130/#127).
5. Implementar IBOV persistido e TWR dedicado.
6. Retomar pré-produção somente após a certificação da #227.
7. Iniciar #246 + #57 apenas depois da base estabilizada.
