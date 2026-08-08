# Migração da superfície administrativa de bootstrap — 07/08/2026

Issues: #247, #248

## Estado canônico

O SGI v2 possui agora uma superfície administrativa dedicada ao bootstrap global:

- `POST /api/v1/admin/bootstrap` — reserva e agenda `run_system_bootstrap()`;
- `GET /api/v1/admin/bootstrap/status` — expõe readiness e reserva de execução.

A reserva é feita por `system_bootstrap_trigger_service.py` e impede agendamentos concorrentes antes mesmo do início da BackgroundTask.

O router `admin_bootstrap.py` não importa providers nem executores isolados de seed/backfill. Toda ingestão externa ampla deve convergir para `run_system_bootstrap()`.

## Portas legadas ainda em migração

`admin.py` ainda contém temporariamente:

- `POST /api/v1/admin/assets/seed`;
- `POST /api/v1/admin/prices/backfill`.

Essas portas estão caracterizadas por teste e devem ser removidas no próximo diff cirúrgico de `admin.py`. A remoção não deve afetar:

- gestão de usuários/configurações;
- backup/restore;
- auditoria;
- manutenção local de snapshots.

## Fronteira preservada

Backfill de snapshots é reconstrução local/derivada e permanece separado do bootstrap de providers.

Após a retirada das duas portas legadas, `POST /api/v1/admin/bootstrap` será a única porta HTTP de ingestão externa ampla do sistema.
