# Auditoria arquitetural — Proventos

> Issue de controle: [#165](https://github.com/lfragoso93-web/sig-v2/issues/165)
>
> Estado auditado: início da Fase 2, após a promoção da Página Resumo para a `main`.

## Objetivo

Mapear o fluxo atual de Proventos antes de qualquer mudança funcional, preservar as entregas válidas das Issues #92 e #95 e orientar a consolidação do módulo em blocos pequenos e testáveis.

## Arquitetura atual

| Camada | Responsabilidade atual | Componentes principais |
|---|---|---|
| Evento global | Armazena eventos conhecidos por ativo, independentemente da carteira | `AssetDividend` |
| Direito da carteira | Materializa quantidade elegível e valor do investidor | `Dividend`, `dividend_backfill_service` |
| Coleta | Busca e normaliza eventos de mercado | pipeline de mercado, sincronização diária e serviços BRAPI |
| Leitura/API | Reconcilia e agrega resumo, lista, histórico e distribuição | `proventos_service`, router `/proventos` |
| Frontend | Exibe KPIs, filtros, gráfico e tabela | `ProventosPage`, hooks e serviço HTTP |

## Contratos temporais e financeiros

1. A data de corte/registro define a elegibilidade da posição.
2. A data de pagamento define o reconhecimento do fluxo de caixa.
3. Dividendos, JCP e amortizações são eventos monetários.
4. Bonificações e demais eventos não monetários não podem compor valores, KPIs ou gráficos financeiros.
5. A página deve consumir exclusivamente dados persistidos; provedores externos pertencem aos pipelines.
6. A materialização deve ser idempotente e rastreável ao evento global que a originou.

## Endpoints auditados

| Endpoint | Finalidade | Filtros atuais |
|---|---|---|
| `GET /proventos/summary` | KPIs consolidados | ano, status, classe e tipo |
| `GET /proventos` | tabela paginada | ano, status, classe e tipo |
| `GET /proventos/history` | série histórica | status, classe e tipo |
| `GET /proventos/distribution` | distribuição mensal | apenas quantidade de meses |

A distribuição não recebe o mesmo conjunto de filtros dos demais componentes. Assim, o gráfico pode representar um universo diferente dos KPIs e da tabela quando o usuário filtra a página.

## Achados

### P1 — Processamento sobreposto no scheduler

A sincronização diária de Proventos e o pipeline de mercado podem coletar e materializar os mesmos eventos em execuções distintas. A idempotência reduz duplicações persistidas, mas não elimina custo, concorrência nem complexidade operacional.

### P1 — Escrita durante leitura

Os quatro endpoints acionam a reconciliação por `ensure_portfolio_proventos`. Não há chamada externa nesse caminho, porém uma consulta da página pode escrever no banco. O estado correto deve ser produzido por seed, onboarding, pipeline ou tarefa explícita; a leitura deve tornar-se previsível e observável.

### P1 — Filtros divergentes

Resumo, lista, histórico e distribuição não compartilham um contrato único. A divergência precisa ser caracterizada por testes antes da correção.

### P2 — Serviços de coleta paralelos

`dividends_sync_service.py` mantém uma implementação específica de FIIs enquanto o pipeline unificado e `dividend_backfill_service` cobrem coleta e materialização. Consumidores e diferenças de regra devem ser comprovados antes da remoção.

### P2 — Contratos de resposta implícitos

Os endpoints não possuem modelos Pydantic estritos de resposta. O frontend replica interfaces TypeScript manualmente, sem validação de execução. Mudanças de shape podem passar despercebidas entre backend e frontend.

### P2 — Modelo com campos duplicados

`Dividend` preserva pares canônicos e legados para datas, quantidade e valor unitário. A compatibilidade é útil durante a transição, mas amplia a possibilidade de divergência. A remoção física deve ser planejada junto ao rebuild pré-produção da Issue #158.

### P2 — Vínculo global anulável

`Dividend.asset_dividend_id` ainda pode ser nulo. Direitos antigos ou criados por caminhos paralelos podem não ter rastreabilidade completa ao evento global.

### P2 — Identidade do evento

A unicidade de `AssetDividend` considera ativo, data ex e tipo. É necessário validar eventos legítimos do mesmo tipo na mesma data e definir uma chave canônica que suporte reprocessamento sem colidir nem duplicar.

### P2 — Regras financeiras espalhadas

O cálculo da posição elegível existe em mais de um serviço. O JCP líquido usa o fator fixo de 85%. Essas regras precisam de uma única implementação, contrato documentado e testes de borda.

### P3 — Lacunas de frontend

Os anos do filtro são limitados a uma janela fixa, há rótulos sem padronização textual e o cliente mantém uma operação de sincronização que não é usada pela página auditada. Também faltam testes de integração dos filtros e estados principais.

## Riscos preservados fora do escopo

As dependências #146, #138, #137 e #133 não serão alteradas durante esta fase. Qualquer impacto observado será registrado na Issue #165 e na Issue #159.

## Estratégia de consolidação

1. Adicionar testes de caracterização do comportamento atual.
2. Criar contratos estritos e um objeto de filtros comum para todos os agregados.
3. Tornar a leitura independente de materialização.
4. Centralizar elegibilidade, posição e regras monetárias.
5. Consolidar coleta e agendamento, removendo duplicidades somente após teste de consumidores.
6. Normalizar o modelo com migração compatível e coordenada com #158.
7. Validar ações, FIIs, ETFs e BDRs em seed, coleta e materialização.
8. Revisar frontend e então executar a melhoria #131.
9. Sincronizar documentação e promover o bloco estrutural à `main`.

## Primeiro bloco de implementação recomendado

Criar testes de caracterização para:

- consistência dos filtros entre resumo, lista, histórico e distribuição;
- exclusão de eventos não monetários;
- elegibilidade por data de corte/registro;
- reconhecimento por data de pagamento;
- idempotência da materialização;
- ausência de chamadas externas nos endpoints de leitura.

Somente depois desses testes o contrato da distribuição deve ser alterado.
