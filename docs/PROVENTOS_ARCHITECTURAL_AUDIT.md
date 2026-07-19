# Auditoria arquitetural — Proventos

> Issue de controle: [#165](https://github.com/lfragoso93-web/sig-v2/issues/165)
>
> Estado auditado: 19/07/2026, após a conclusão dos itens 1 a 6 da Fase 2.

## Objetivo

Manter o fluxo de Proventos DB-first, rastreável e coerente entre catálogo
global, direito da carteira, API e frontend, preservando as entregas válidas das
Issues #92 e #95.

## Arquitetura vigente

| Camada | Responsabilidade | Componentes principais |
|---|---|---|
| Evento global | Armazena eventos de todos os ativos do catálogo, independentemente de posição | `AssetDividend` |
| Direito da carteira | Materializa quantidade elegível e valores bruto/líquido | `Dividend`, serviço de elegibilidade |
| Coleta | Busca e normaliza eventos uma vez por dia útil | sincronização diária e pipeline canônico |
| Leitura/API | Autoriza e agrega sem escrita ou acesso a provedor | `proventos_service`, router `/proventos` |
| Frontend | Exibe KPIs, filtros, gráfico e tabela | `ProventosPage`, hooks e serviço HTTP |

A coleta global usa o catálogo de `assets` por padrão. A posição do investidor é
consultada somente na materialização, pela data de corte/registro do evento.

## Contratos temporais e financeiros

1. A data de corte/registro define a elegibilidade da posição.
2. A data de pagamento define o reconhecimento do fluxo de caixa.
3. Dividendos, JCP, rendimentos e amortizações são eventos monetários.
4. Bonificações, subscrições e demais eventos não monetários não compõem KPIs ou gráficos financeiros.
5. A página consome exclusivamente dados persistidos.
6. A materialização é idempotente e rastreável ao evento global.

## Endpoints canônicos

| Endpoint | Finalidade | Filtros compartilhados |
|---|---|---|
| `GET /proventos/summary` | KPIs consolidados | ano, status, classe e tipo |
| `GET /proventos` | tabela paginada | ano, status, classe e tipo |
| `GET /proventos/history` | série histórica | ano, status, classe e tipo |
| `GET /proventos/distribution` | distribuição mensal ou anual | meses, ano, status, classe e tipo |

Os quatro endpoints possuem contratos Pydantic estritos. Backend e frontend
usam o mesmo universo de filtros e as leituras não materializam direitos.

## Itens consolidados

### Agenda e coleta global

A coleta ocorre uma vez em dias úteis, às 18:10, para todos os ativos nacionais
elegíveis do catálogo. O pipeline noturno processa preços e logos com eventos e
materialização desativados. `only_held=True` existe apenas como opção operacional
explícita.

### Leitura, mutação e elegibilidade

Leituras executam somente autorização e agregação. Mutações de transações
disparam reconciliação explícita para recalcular ou remover direitos. O cálculo
de posição na data de corte é compartilhado pelos fluxos de materialização e
reconciliação.

### Serviço FII legado

O sincronizador FII paralelo, o cliente batch e a configuração exclusiva foram
removidos. Uma auditoria posterior encontrou duas rotas administrativas
residuais que ainda importavam o serviço removido; elas foram eliminadas no
commit `fcc7bb34c22eb3a06673d68d2043c7818dfd94d1`. Não havia consumidor no
frontend. `dividends_sync_jobs` permanece apenas para contração controlada na
Issue #158.

### Modelo legado e rastreabilidade

O inventário read-only e o dry-run de vínculos foram implementados. A execução
real via Docker Compose em 19/07/2026 retornou `scanned: 0` e zero em todas as
categorias de risco. Assim, nenhum backfill deve ser aplicado nesta base. A
remoção física dos campos duplicados e a eventual restrição `NOT NULL` continuam
reservadas à #158.

### Matriz por classe

| Classe | Seed | Coleta global sem posição | Materialização rastreável | Reprocessamento sem duplicar |
|---|---:|---:|---:|---:|
| Ação | validado | validado | validado | validado |
| FII | validado | validado | validado | validado |
| ETF nacional | validado | validado | validado | validado |
| BDR | validado | validado | validado | validado |

A matriz usa eventos monetários, posição anterior à data de corte e verifica
quantidade, valor bruto, valor líquido e `asset_dividend_id`.

## Pendências arquiteturais

### P2 — Identidade do evento

A unicidade de `AssetDividend` ainda considera ativo, data ex e tipo. Antes de
alterá-la, é necessário comprovar com dados de provedor como representar eventos
legítimos do mesmo tipo e data sem colidir ou duplicar.

### P2 — Regras financeiras por tipo

O JCP líquido ainda usa fator fixo de 85%. Dividendos, JCP, rendimentos,
amortizações e eventos não monetários precisam de matriz explícita de
classificação, valores e bordas antes da revisão do frontend.

### P3 — Frontend

Ainda faltam a revisão dos estados principais, gráficos, tabelas, indicadores,
acessibilidade e testes de integração da página. O detalhamento mensal permanece
acompanhado pela Issue #131.

## Riscos preservados fora do escopo

As dependências #146, #138, #137 e #133 não são alteradas nesta fase. Qualquer
impacto observado deve ser registrado nas Issues #165 e #159.

## Sequência da consolidação

1. ~~Caracterizar o comportamento e documentar a arquitetura.~~ Concluído.
2. ~~Criar contratos estritos e filtros compartilhados.~~ Concluído.
3. ~~Separar leitura de materialização e centralizar elegibilidade.~~ Concluído.
4. ~~Consolidar coleta e scheduler; remover o serviço FII paralelo.~~ Concluído.
5. ~~Inventariar o modelo e preparar a migração segura com a #158.~~ Concluído.
6. ~~Validar seed, coleta e materialização para ações, FIIs, ETFs e BDRs.~~ Concluído.
7. Validar classificação e valores por tipo de evento.
8. Revisar frontend e implementar a melhoria #131.
9. Sincronizar README, ROADMAP e CHANGELOG e promover o bloco estrutural à `main`.

## Próximo bloco recomendado

Criar a matriz de eventos monetários e não monetários: dividendos, JCP,
rendimentos, amortizações, bonificações e subscrições. A matriz deve validar
normalização, bruto, líquido, exclusão dos agregados financeiros e idempotência.
