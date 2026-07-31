# Auditoria arquitetural — Proventos

> Issue funcional de controle: [#165](https://github.com/lfragoso93-web/sig-v2/issues/165)  
> Seed isolado de pré-produção: [#226](https://github.com/lfragoso93-web/sig-v2/issues/226)  
> Contrato operacional: `pre-prod-dividends-seed.v2`
>
> Estado funcional auditado: 19/07/2026, após a conclusão técnica e documental da Fase 2.  
> Fronteira operacional atualizada: 28/07/2026.

## Objetivo

Manter o fluxo de Proventos DB-first, rastreável e coerente entre catálogo
global, direito da carteira, API e frontend, preservando as entregas válidas das
Issues #92 e #95.

## Fronteira operacional de pré-produção

A arquitetura funcional vigente não é uma entrada segura para o rebuild real:
as portas públicas mutáveis e a materialização do scheduler, do pipeline de
mercado, da CLI dedicada, do seed histórico e do `full_market_rebuild` foram
contraídas, mas o backfill pós-transação ainda oferece caminhos que não
garantem rollback integral do estágio.

A Issue #226 isola a evolução operacional no contrato `docs/PRE_PROD_DIVIDENDS_SEED_CONTRACT.md`. O estágio v2 lê somente `assets` e `asset_dividends` e escreve somente em `asset_dividends`; a inspeção de `dividends_sync_jobs` foi retirada.

A implementação usa uma única entrada, advisory lock dedicado, uma transação de trabalho, fontes explícitas sem fallback silencioso, métricas da persistência global e comparador offline de duas execuções. Migration de unicidade, conversão cambial, mudanças no frontend, posições e snapshots ficam fora do escopo.

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
| `GET /proventos/historico-mensal` | série histórica e composição mensal por classe | ano, status, classe e tipo |
| `GET /proventos/distribuicao` | distribuição mensal ou anual | meses, ano, status, classe e tipo |

Os quatro endpoints possuem contratos Pydantic estritos. Backend e frontend
usam o mesmo universo de filtros e as leituras não materializam direitos.

## Itens consolidados

### Agenda e coleta global

A coleta ocorre uma vez em dias úteis, às 18:10, para todos os ativos nacionais
elegíveis do catálogo. O pipeline noturno processa preços e logos com eventos e
materialização desativados. `only_held=True` existe apenas como opção operacional
explícita.

As CLIs e o serviço batch do pipeline de mercado não aceitam mais a opção
`materialize`; eles coletam somente eventos globais. A CLI dedicada de
Proventos e o seed histórico também persistem somente eventos globais, sem
materializar direitos por carteira.

O `full_market_rebuild` preserva a etapa de sincronização global, mas seu
resumo operacional contabiliza somente ativos varridos, sincronizados e falhos.
Ele não importa, chama ou anuncia materialização de direitos por carteira.

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
frontend. O modelo ORM de `dividends_sync_jobs` foi removido; a migration
histórica e a migration de contração física permanecem autocontidas, sem leitura
de runtime. A execução física continua reservada à Issue #158.

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

### Regras financeiras por tipo

| Tipo | Evento global | Direito financeiro | Regra do líquido | Agregados financeiros |
|---|---:|---:|---:|---:|
| Dividendo | sim | sim | 100% do bruto | inclui |
| JCP | sim | sim | 85% do bruto | inclui o líquido |
| Rendimento | sim | sim | 100% do bruto | inclui |
| Amortização | sim | sim | 100% do bruto | inclui |
| Bonificação | sim | não | não aplicável | exclui |
| Subscrição | sim | não | não aplicável | exclui |

A normalização dos seis tipos é canônica e testada. A função
`calculate_net_value` concentra a regra de líquido usada por coleta,
materialização e reconciliação. Mesmo direitos legados não monetários com
valores indevidos são excluídos dos KPIs, histórico e distribuição e aparecem
na lista identificados por `is_cash=false`.

### Frontend e estados da página

As interfaces TypeScript refletem os campos obrigatórios e enums do contrato
Pydantic. A página diferencia loading, erro e vazio em indicadores,
distribuição, histórico e lista, sem converter falha em zero. Os filtros usam o
mesmo objeto nos quatro hooks, possuem nomes acessíveis e expõem seleção por
`aria-pressed`.

A tabela confia no `is_cash` canônico, apresenta estados pendente/cancelado com
rótulos próprios e nunca exibe valores legados de eventos não monetários como
dinheiro. O cliente e o hook de sincronização manual sem consumidores foram
removidos. Testes de fluxo cobrem carteira ausente, estados da consulta,
propagação dos filtros, vazio e semântica da tabela.

### Detalhamento mensal por classe

O histórico mensal agrega ano, mês e classe em uma única consulta. O payload
preserva `months`, `total` e `media` e acrescenta `month_details` apenas
para meses positivos. Cada detalhe reutiliza o catálogo canônico de rótulos,
ordena as classes por valor e deriva o total das mesmas parcelas monetárias
arredondadas exibidas, garantindo reconciliação.

As células com composição abrem um popover renderizado em portal, ajustado às
bordas da viewport e acessível por hover, foco, teclado e toque. `Esc`, saída da
área interativa e toque/clique externo fecham o detalhe. Meses vazios permanecem
não interativos.

### Evidências finais

- Backend: 78 testes aprovados.
- Frontend: 48 testes aprovados.
- TypeScript: typecheck aprovado.
- Dry-run do vínculo legado: nenhum registro ou risco encontrado na base validada.
- Branch: `stable-15jun` à frente da `main` e sem divergência na auditoria pré-PR.
- Dependências #146, #138, #137 e #133: preservadas sem alteração.

## Pendências arquiteturais

### P2 — Identidade do evento

A unicidade de `AssetDividend` ainda considera ativo, data ex e tipo. Antes de
alterá-la, é necessário comprovar com dados de provedor como representar eventos
legítimos do mesmo tipo e data sem colidir ou duplicar.

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
7. ~~Validar classificação e valores por tipo de evento.~~ Concluído.
8. ~~Revisar frontend, gráficos, tabelas, indicadores, estados e contratos.~~ Concluído.
9. ~~Implementar o detalhamento mensal da Issue #131.~~ Concluído.
10. ~~Sincronizar README, ROADMAP e CHANGELOG.~~ Concluído; promoção para a `main` pela PR estrutural.

## Próximo bloco recomendado

O envelope inicial `pre-prod-dividends-seed.v1` foi substituído pelo contrato canônico v2 na Issue #226.
