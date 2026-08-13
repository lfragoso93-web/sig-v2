# Inventário de consumidores — câmbio e metas

> Issue: #241  
> Data: 06/08/2026  
> Branch: `stable-15jun`

## Objetivo

Classificar os consumidores atuais de `fx_rates` e `goal_allocations` antes de qualquer decisão de migration, reintrodução ORM ou remoção física.

## Câmbio

### Evidência atual

- Existe um endpoint ativo `GET /usd-brl` em `backend/app/routers/fx.py`.
- O endpoint chama diretamente `app.integrations.fx_rate.get_usd_brl`.
- A integração consulta BRAPI em tempo de request e retorna fallback fixo `5.40` em caso de erro.
- O README e o ROADMAP descrevem o câmbio como persistido e DB-first.
- A tabela migrada `fx_rates` permanece fora do agregador ORM atual.

### Classificação

`fx_rates` não deve ser tratado como tabela órfã descartável. O domínio de câmbio ainda possui consumidor funcional, mas o consumidor atual está arquiteturalmente desviado por:

1. consultar provedor durante request;
2. não ler a série persistida;
3. converter falha/ausência em um valor fixo artificial.

### Decisão provisória

- preservar `fx_rates`;
- não criar drop migration;
- não reintroduzir modelo ORM apenas para silenciar `alembic check`;
- abrir bloco próprio para migrar `/usd-brl` para leitor persistido DB-first;
- ausência de cotação persistida deve ser explícita, nunca convertida em fallback financeiro silencioso;
- chamadas a BRAPI devem permanecer em pipelines operacionais opt-in, não em cálculos ou formulários read-only.

## Metas

### Evidência atual

O fluxo produtivo de metas usa:

- `frontend/src/pages/MetasPage.tsx`;
- `frontend/src/hooks/useGoals.ts`;
- `backend/app/routers/goals.py`;
- `backend/app/services/goals_service.py`;
- `backend/app/models/goal.py`;
- tabela `goals`.

O frontend cria e acompanha metas dos tipos `PATRIMONIO`, `PROVENTOS`, `RENTABILIDADE` e `LIVRE`. O service resolve valores atuais com posições, direitos canônicos de Proventos e snapshots.

Nenhum consumidor atual usa `goal_allocations`, `goal_id + asset_type + target_percentage` ou relacionamento equivalente.

### Classificação

`goal_allocations` é schema legado sem consumidor runtime comprovado. A capacidade funcional atual de metas não depende dessa tabela.

### Decisão provisória

- preservar temporariamente a tabela migrada;
- não reintroduzir modelo ORM;
- não remover até existir fixture sintética e decisão explícita sobre compatibilidade de dados;
- eventual remoção deve ocorrer em bloco exclusivo de metas, após comprovar tabela vazia ou migrar dados relevantes;
- o contrato canônico atual de metas permanece `goals` por carteira.

## Consequência para o `alembic check`

A deriva de `fx_rates` e `goal_allocations` não pode ser resolvida por autogenerate global. Cada domínio exige decisão própria:

- câmbio: primeiro migrar consumidor ativo para leitura persistida;
- metas: primeiro certificar ausência de consumidores e dados relevantes.

## Próximos blocos

1. criar política executável para câmbio DB-first e metas canônicas;
2. adicionar gates contra chamada de provider no router de câmbio;
3. implementar leitor persistido de USD/BRL em bloco separado, com testes;
4. criar fixture sintética para decisão futura sobre `goal_allocations`.
