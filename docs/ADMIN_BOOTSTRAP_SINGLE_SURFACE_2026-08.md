# Superfície administrativa única de bootstrap — 2026-08

## Decisão

A ingestão externa ampla do SGI v2 possui uma única superfície HTTP administrativa:

- `POST /api/v1/admin/bootstrap`
- `GET /api/v1/admin/bootstrap/status`

Esses endpoints delegam exclusivamente ao orquestrador global `system-bootstrap.v1` e ao estado de readiness.

## Portas removidas

As superfícies paralelas abaixo foram removidas:

- `POST /api/v1/admin/assets/seed`
- `POST /api/v1/admin/prices/backfill`
- `GET /api/v1/admin/prices/backfill/status`

Seed de catálogo e histórico amplo de preços pertencem ao bootstrap global e não podem voltar a existir como operações HTTP independentes.

## Manutenções que permanecem separadas

As operações abaixo não representam ingestão externa ampla e permanecem administrativas:

- backfill/rebuild local de snapshots;
- backup/restore de banco;
- gestão de usuários e configuração;
- auditoria.

## Fronteira de providers

Após o bootstrap certificado, consultas externas recorrentes continuam restritas a:

1. preço intraday;
2. fechamento diário;
3. resolução pontual de lacuna histórica para uma data necessária, com persistência antes do uso financeiro.

Nenhuma dessas regras altera `goals` nem libera `ready_for_real_data=true` antes da conclusão integral da Issue #248.

## Gates

Os testes estruturais devem:

- percorrer a árvore efetiva de rotas do FastAPI moderno;
- garantir presença única de `/admin/bootstrap` e `/admin/bootstrap/status`;
- impedir reintrodução das três portas legadas;
- preservar as rotas administrativas locais de snapshots.
