# Auditoria arquitetural — seed isolado de câmbio

## Contexto

Este documento registra a auditoria inicial da Issue #217 antes de qualquer implementação do seed de câmbio. O estágio deve permanecer isolado de benchmarks, B3, Tesouro, proventos, importação CSV, posições, snapshots e `full_market_rebuild`.

## Achados confirmados

- A Issue #130 já prevê câmbio histórico, PTAX, valor em BRL na data da operação e separação entre retorno do ativo e efeito cambial.
- Não foi localizada, pela busca indexada do repositório, uma CLI, serviço, model ou tabela com nomenclatura dedicada e inequívoca de câmbio (`fx`, `exchange_rate`, `currency_rate`, `ptax`, `USD/BRL`).
- A ausência de resultado na busca indexada não prova inexistência da lógica: ela pode estar embutida em providers genéricos, valuation, importação ou persistência de preços.
- Não há PR aberta neste checkpoint.
- `stable-15jun` está sincronizada com `main` no sentido de não possuir commits pendentes da base; a branch segue à frente com o bloco de benchmarks ainda não promovido.

## Riscos arquiteturais

1. Persistir câmbio em `asset_prices` sem identidade explícita de par, fonte e convenção de cotação pode misturar preço de ativo com taxa cambial.
2. Consultar cotação sob demanda em valuation ou frontend quebra o princípio DB-first e impede reconstrução auditável.
3. Fallback silencioso entre PTAX, brapi ou outro provider pode alterar valores históricos sem evidência.
4. Representar USD/BRL e BRL/USD sem convenção canônica pode produzir inversões e duplicidades.
5. Reutilizar o seed macro para câmbio acoplaria fontes, tabelas e critérios de cobertura distintos.
6. Antecipar decomposição de performance cambial neste estágio ampliaria indevidamente o escopo da Issue #217.

## Decisões preliminares

- Câmbio deve possuir estágio operacional próprio, separado do seed macro e de proventos.
- A primeira implementação deve cobrir somente persistência canônica e auditável de taxas cambiais.
- A fonte primária e a convenção dos pares precisam ser explicitadas antes do contrato.
- Nenhuma tabela será autorizada para escrita até o inventário localizar a persistência real ou concluir que uma estrutura dedicada é necessária.
- O contrato deve registrar, por par: quantidade de linhas, primeira data, última data, duplicidades, fonte e direção da cotação.
- A idempotência deve ser comprovada pelo estado persistido, e não apenas pelo número de linhas processadas pelo provider.

## Inventário ainda obrigatório

- [ ] listar arquivos em `backend/app/integrations`, `backend/app/services`, `backend/app/models`, `backend/app/api` e `backend/app/cli` relacionados a moeda, dólar, conversão e preço internacional;
- [ ] localizar referências a `USD`, `BRL`, `EUR`, `currency`, `exchange`, `forex`, `ptax` e símbolos equivalentes;
- [ ] identificar schedulers ou jobs que atualizem valores internacionais;
- [ ] mapear persistência atual e constraints;
- [ ] identificar consumidores em BDR, ETF internacional, cripto, patrimônio, rentabilidade e importação;
- [ ] confirmar provider atual, autenticação, timeout, retry, rate limit e fallback;
- [ ] decidir se será reutilizada uma tabela existente ou criada uma tabela cambial dedicada;
- [ ] registrar duplicações, endpoints obsoletos e documentação divergente.

## Contrato proposto após o inventário

Nome provisório: `pre-prod-fx-seed.v1`.

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

1. concluir inventário técnico por arquivo e referência;
2. decidir fonte, pares e persistência canônica;
3. criar contrato puro;
4. criar inspeção read-only;
5. adaptar o importador real para sessão externa e `commit=False`, se necessário;
6. criar orquestrador transacional e advisory lock;
7. criar CLI, testes, wrapper e comparador offline;
8. executar duas vezes e preservar evidências;
9. sincronizar README, ROADMAP, CHANGELOG e Issues #217, #216 e #158.
