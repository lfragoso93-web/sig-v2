# Auditoria arquitetural — seed isolado de câmbio

## Contexto

Este documento registra a auditoria da Issue #217 antes de qualquer implementação do seed de câmbio. O estágio deve permanecer isolado de benchmarks, B3, Tesouro, proventos, importação CSV, posições, snapshots e `full_market_rebuild`.

## Achados confirmados

- A Issue #130 já prevê câmbio histórico, PTAX, valor em BRL na data da operação e separação entre retorno do ativo e efeito cambial.
- Não foi localizada, pela busca indexada do repositório, uma CLI, serviço, model ou tabela com nomenclatura dedicada e inequívoca de câmbio (`fx`, `exchange_rate`, `currency_rate`, `ptax`, `USD/BRL`).
- A ausência de resultado na busca indexada não prova inexistência da lógica: ela pode estar embutida em providers genéricos, valuation, importação ou persistência de preços.
- O model `Asset` possui moeda explícita (`BRL`, `USD`, `EUR`, `BTC`) e campos de roteamento de provider, portanto ativos internacionais já possuem identidade monetária no catálogo.
- O model `AssetPrice` representa preço histórico de ativo, possui unicidade por `asset_id + timestamp`, fonte textual e relação obrigatória com `assets`; não possui campos explícitos de moeda base, moeda cotada, direção do par ou tipo de taxa.
- A documentação do próprio model `AssetPrice` afirma que ele é alimentado pelo scheduler via BRAPI, mas a busca indexada não expôs um fluxo cambial dedicado nem um ativo canônico de par.
- Não há PR aberta neste checkpoint.
- `stable-15jun` está sem commits pendentes da `main`, embora permaneça à frente com o bloco estrutural ainda não promovido.

## Evidências por arquivo

### `backend/app/models/asset.py`

- Tipos internacionais existentes: `ETF_INTERNACIONAL`, `STOCK`, `CRIPTO` e `BDR`.
- Moedas previstas: `BRL`, `USD`, `EUR` e `BTC`.
- `currency` é um atributo do ativo, não uma série cambial.
- `provider` e `provider_symbol` permitem roteamento, mas não definem contrato cambial.

### `backend/app/models/asset_price.py`

- Tabela: `asset_prices`.
- Constraint: `uq_price_asset_timestamp`.
- Campos financeiros: `open`, `high`, `low`, `close`, `volume`.
- Campo de origem: `source`.
- Não existem campos `base_currency`, `quote_currency`, `pair`, `rate_type` ou `fixing_date`.

## Conclusão sobre persistência

`asset_prices` não deve ser autorizada automaticamente como tabela canônica de câmbio. Ela só seria reutilizável se o par cambial fosse modelado como um `Asset` explícito e se a convenção de cotação, fonte, timezone e cobertura fossem formalizadas. No estado atual, essa reutilização produziria ambiguidade entre preço de ativo e taxa cambial.

A recomendação arquitetural é criar persistência dedicada, sujeita à confirmação do inventário local completo:

- tabela sugerida: `fx_rates`;
- identidade única: `base_currency + quote_currency + reference_date + rate_type + source`;
- campos mínimos: taxa, data/hora da observação, data de referência, fonte, tipo de taxa, criado/atualizado;
- par inicial do rebuild: `USD/BRL`;
- direção canônica: unidades de BRL por 1 unidade de USD;
- EUR e demais pares ficam fora do primeiro estágio até existir consumidor real e fonte aprovada.

## Fonte canônica proposta

Para o estágio inicial, a fonte primária deve ser oficial e independente do provider genérico de ativos. A PTAX do Banco Central é a candidata preferencial para histórico diário auditável. BRAPI ou outro provider comercial só deve atuar como fallback explícito, registrado na evidência e nunca silencioso.

Esta decisão ainda exige validação local dos módulos de integração e configuração antes de implementação.

## Consumidores mapeados conceitualmente

- `STOCK` e `ETF_INTERNACIONAL`: necessitam conversão para BRL quando o preço persistido está em USD.
- `CRIPTO`: pode usar par em USD ou BRL dependendo do provider; não deve assumir conversão uniforme.
- `BDR`: normalmente possui preço local em BRL e não deve ser convertido novamente.
- Patrimônio e Rentabilidade: devem consumir taxa persistida e nunca consultar provider sob demanda.
- Importação CSV: poderá usar taxa histórica na data da operação, mas essa integração permanece fora do escopo do seed.

## Riscos arquiteturais

1. Persistir câmbio em `asset_prices` sem identidade explícita de par, fonte e convenção de cotação pode misturar preço de ativo com taxa cambial.
2. Consultar cotação sob demanda em valuation ou frontend quebra o princípio DB-first e impede reconstrução auditável.
3. Fallback silencioso entre PTAX, BRAPI ou outro provider pode alterar valores históricos sem evidência.
4. Representar USD/BRL e BRL/USD sem convenção canônica pode produzir inversões e duplicidades.
5. Reutilizar o seed macro para câmbio acoplaria fontes, tabelas e critérios de cobertura distintos.
6. Antecipar decomposição de performance cambial neste estágio ampliaria indevidamente o escopo da Issue #217.
7. Converter BDR novamente para BRL criaria dupla conversão.
8. Usar preço intradiário para operações históricas sem política de fixing produziria resultados não reproduzíveis.

## Decisões arquiteturais do estágio

- Câmbio terá estágio operacional próprio, separado do seed macro e de proventos.
- O primeiro estágio cobrirá somente persistência canônica de `USD/BRL`.
- Convenção canônica: BRL por 1 USD.
- Fonte primária proposta: PTAX/BCB.
- `asset_prices` não será autorizada para escrita cambial no primeiro desenho.
- O contrato registrará por par: quantidade de linhas, primeira e última datas, duplicidades, fonte, direção e tipo de taxa.
- A idempotência será comprovada pelo estado persistido, não pelo número de linhas submetidas ao UPSERT.
- Conversão de valuation, importação e decomposição de performance permanecem fora do estágio operacional.

## Inventário local ainda obrigatório

- [ ] listar arquivos reais em `backend/app/integrations`, `backend/app/services`, `backend/app/models`, `backend/app/api` e `backend/app/cli` relacionados a moeda, dólar, conversão e preço internacional;
- [ ] localizar referências não indexadas a `USD`, `BRL`, `EUR`, `currency`, `exchange`, `forex`, `ptax` e símbolos equivalentes;
- [ ] identificar schedulers ou jobs que atualizem valores internacionais;
- [x] mapear `assets` e `asset_prices` como estruturas existentes relevantes;
- [ ] confirmar consumers reais no código de BDR, ETF internacional, cripto, patrimônio, rentabilidade e importação;
- [ ] confirmar autenticação, timeout, retry, rate limit e fallback do provider atual;
- [ ] confirmar se já existe integração BCB/PTAX não encontrada pelo índice;
- [ ] validar necessidade da migration e model `fx_rates`;
- [ ] registrar duplicações, endpoints obsoletos e documentação divergente.

## Contrato proposto

Nome: `pre-prod-fx-seed.v1`.

Campos mínimos:

- identidade operacional: `run_id`, branch e SHA;
- fonte e versão do provider;
- pares autorizados e convenção canônica;
- baseline e pós-contagem por par;
- cobertura temporal;
- criados, atualizados, ignorados e removidos;
- duplicidades e referências órfãs;
- tabelas autorizadas;
- duração, erros e estado final;
- `ok` somente após reconciliação completa.

## Sequência recomendada

1. validar o inventário local completo e confirmar que não existe integração PTAX reutilizável;
2. criar migration/model dedicado `fx_rates`, se a ausência for confirmada;
3. criar contrato puro `pre-prod-fx-seed.v1`;
4. criar inspeção read-only;
5. implementar cliente PTAX isolado e importador com sessão externa e `commit=False`;
6. criar orquestrador transacional e advisory lock;
7. criar CLI, testes, wrapper e comparador offline;
8. executar duas vezes e preservar evidências;
9. sincronizar README, ROADMAP, CHANGELOG e Issues #217, #216 e #158.
