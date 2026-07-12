# Inventário da integração de dados de mercado

**Issue:** #130  
**Branch:** `stable-15jun`  
**Atualizado em:** 12 de julho de 2026

## Objetivo

Registrar o estado atual da integração antes da migração incremental para contratos v2 tipados. Este documento é interno e não deve expor credenciais, payloads sensíveis ou detalhes em respostas públicas.

## Estado atual

A integração está concentrada principalmente em `backend/app/integrations/brapi.py`, que atualmente acumula responsabilidades de:

- autenticação e configuração;
- catálogo e validação de tickers;
- cotações atuais;
- histórico de preços;
- catálogo e preços do Tesouro Direto;
- catálogo e cotações de criptomoedas;
- proventos de ações e FIIs;
- busca e sugestões de ativos;
- normalização de símbolos;
- caches em memória e fallback entre contratos.

A arquitetura já utiliza alguns endpoints v2, mas ainda mantém chamadas de contratos anteriores e parsing permissivo para múltiplas formas de resposta.

## Endpoints identificados

| Domínio | Endpoint atual | Contrato | Observação |
|---|---|---|---|
| Cotações nacionais | `/quote/{symbols}` | legado | Suporta lote de até 20 símbolos e fallback unitário em erro 400. |
| Catálogo de ativos | `/v2/tickers` | v2 | Paginação manual por `page` e `limit`. |
| Validação de ticker | `/v2/tickers` | v2 | Busca individual; ainda não utiliza resolução oficial de renomes. |
| Catálogo de cripto | `/v2/crypto/available` | v2 | Busca e paginação próprias. |
| Histórico de ações | `/v2/stocks/historical` | v2 | Preferencial para janelas customizadas. |
| Histórico amplo | `/quote/{ticker}?range=max` | legado | Fallback para históricos longos. |
| Proventos de ações | `/v2/stocks/dividends` | v2 | Lote de até 20 símbolos. |
| Proventos de FIIs | `/v2/fii/dividends` | v2 | Lote de até 20 símbolos. |
| Tesouro Direto | endpoints específicos dentro da integração | misto | Possui catálogo, normalização e fallback próprios. |
| Criptomoedas | endpoints específicos dentro da integração | misto | Normalização por código e sufixo. |

## Consumidores internos mapeados

### Cotações e histórico

- serviços de preço atual;
- backfill de histórico;
- snapshots de patrimônio;
- páginas de patrimônio, resumo e rentabilidade;
- enriquecimento do cadastro de ativos;
- rotas de cotação e detalhe de ativo.

### Catálogo e validação

- seed inicial de ativos;
- busca e sugestão de tickers;
- criação manual de ativos;
- importação CSV;
- detecção de tickers indisponíveis;
- cooldown de símbolos inválidos.

### Proventos

- bootstrap histórico;
- sincronização incremental;
- materialização por carteira;
- cálculo e exibição de dividendos e JCP.

### Tesouro Direto

- catálogo canônico;
- reconciliação de títulos já cadastrados;
- histórico de preços;
- atualização de snapshots;
- fallback para títulos sem preço no provedor principal.

## Problemas e riscos encontrados

### 1. Integração monolítica

Um único módulo concentra múltiplos domínios, regras de fallback, parsing e cache. Isso dificulta testes, migração incremental e observabilidade por endpoint.

### 2. Contratos mistos

A integração usa simultaneamente endpoints v2 e legados. Isso torna a depreciação difícil de acompanhar e faz com que cada serviço tenha expectativas diferentes sobre envelopes e campos.

### 3. Parsing excessivamente permissivo

Diversos trechos aceitam alternativas como:

- `results`, `stocks`, `tickers`, `fiis` ou listas diretas;
- `symbol`, `ticker`, `stock`, `fii`;
- `dividends`, `cashDividends`, `data`;
- `date`, `timestamp`, `exDate`, `ex_date`.

Esse comportamento aumenta resiliência, mas pode mascarar mudança de contrato ou erro de plano. O cliente v2 deverá validar schemas explicitamente e registrar incompatibilidades.

### 4. Configuração duplicada

Existe constante de URL no módulo e configuração resolvida em `Settings`. O cliente v2 deve usar exclusivamente a configuração central, evitando divergência entre ambientes.

### 5. Clientes HTTP recriados por chamada

Há múltiplas construções de `httpx.AsyncClient` dentro de funções e loops. O cliente v2 deve centralizar conexão, timeout, retry e headers.

### 6. Cache apenas em memória

Validação de tickers e catálogo do Tesouro usam cache local ao processo. Em múltiplas réplicas, o estado não é compartilhado. Cobertura e aliases relevantes devem ser persistidos; caches operacionais podem usar Redis.

### 7. Falhas tratadas como ticker válido

Em alguns fluxos de validação, erro do provedor faz o ticker ser aceito temporariamente para evitar bloqueio. Isso é útil como fail-open, mas precisa distinguir:

- ticker confirmado;
- ticker desconhecido;
- provider indisponível;
- cobertura não verificada.

### 8. Ausência de resolução oficial de renomes

O SGI ainda não consulta resolução e histórico de renomes antes de criar ou consultar ativos. Isso pode gerar duplicação entre ticker antigo e ticker atual.

### 9. Ausência de cobertura por recurso

O sistema tenta serviços sem consultar previamente se o ativo possui histórico, proventos, indicadores, imóveis, relatórios ou fundamentos disponíveis.

### 10. Bonificações e subscrições

O parser de proventos preserva um campo textual de tipo, mas ainda não separa formalmente eventos em dinheiro de eventos que alteram quantidade ou geram direitos.

## Decisão de arquitetura

A migração será incremental. Não será feita uma substituição total do módulo atual em um único passo.

Estrutura-alvo:

```text
BrapiV2Client
  ├── TickerCatalogClient
  ├── TickerResolutionClient
  ├── AssetCoverageClient
  ├── QuotesClient
  ├── HistoryClient
  ├── DividendsClient
  ├── FiiDataClient
  └── FundamentalsClient
        ↓
DTOs internos tipados
        ↓
Services do SGI
```

Os payloads do fornecedor não devem chegar diretamente a routers ou frontend.

## Ordem incremental validada

1. criar cliente base v2, erros e envelope tipado;
2. implementar resolução de tickers e histórico de renomes;
3. persistir aliases históricos;
4. integrar resolução à importação CSV e criação manual;
5. implementar cobertura por ativo;
6. migrar cotações e histórico;
7. separar proventos em dinheiro de bonificações e subscrições;
8. enriquecer FIIs;
9. enriquecer ações;
10. melhorar câmbio e macroeconomia.

## Primeiro recorte de implementação

O primeiro recorte funcional será **resolução de tickers**, por ter baixo risco e impacto transversal.

Entregáveis previstos:

- DTO `TickerResolution`;
- cliente v2 isolado para resolução em lote;
- serviço com fallback seguro para o ticker original;
- testes com ticker atual, antigo, desconhecido e resposta parcial;
- nenhuma persistência ou alteração automática de ativos neste primeiro commit funcional.

Depois da validação do contrato, serão adicionados `asset_aliases` e integração com importação/criação.

## Critérios do Bloco 0

- [x] endpoints atuais inventariados;
- [x] contratos mistos identificados;
- [x] consumidores internos classificados;
- [x] riscos de migração registrados;
- [x] ordem incremental definida;
- [ ] fixtures v2 sanitizadas;
- [ ] confirmação prática dos recursos liberados pelo token;
- [ ] comparação dos envelopes reais com os DTOs planejados.
