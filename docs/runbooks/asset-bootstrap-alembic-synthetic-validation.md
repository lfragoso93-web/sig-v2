# Validação sintética Alembic do bootstrap canônico

Este roteiro valida a cadeia Alembic em bancos descartáveis. Ele não deve apontar para pré-produção, produção ou qualquer banco com dados reais.

## Escopo

- banco PostgreSQL vazio;
- banco sintético com `alembic_version` e estrutura legada mínima representativa;
- `alembic upgrade head`, `current` e `check`;
- nenhuma carga externa, seed, rebuild ou sincronização.

## Pré-condições

- branch `stable-15jun` sincronizada e working tree limpa;
- Docker Desktop disponível;
- containers `db` e `redis` saudáveis;
- SHA registrado antes da execução;
- Issue #227 mantida como gate para qualquer operação real.

## 1. Confirmar identidade

```powershell
$CommitSha = (git rev-parse HEAD).Trim().ToLowerInvariant()
$CommitSha
```

## 2. Banco vazio descartável

```powershell
$EmptyDb = "sgi_asset_bootstrap_empty"

docker compose exec db psql -U sgi -d postgres `
  -v ON_ERROR_STOP=1 `
  -c "DROP DATABASE IF EXISTS $EmptyDb;"

docker compose exec db psql -U sgi -d postgres `
  -v ON_ERROR_STOP=1 `
  -c "CREATE DATABASE $EmptyDb;"
```

Execute as migrations apontando exclusivamente para o banco descartável conforme o mecanismo de override de URL já adotado pelo projeto. Depois valide:

```powershell
# Dentro do backend, com a URL do banco descartável configurada:
python -m alembic upgrade head
python -m alembic current
python -m alembic check
```

## 3. Estrutura legada sintética

Crie outro banco descartável:

```powershell
$LegacyDb = "sgi_asset_bootstrap_legacy"

docker compose exec db psql -U sgi -d postgres `
  -v ON_ERROR_STOP=1 `
  -c "DROP DATABASE IF EXISTS $LegacyDb;"

docker compose exec db psql -U sgi -d postgres `
  -v ON_ERROR_STOP=1 `
  -c "CREATE DATABASE $LegacyDb;"
```

A estrutura legada deve ser criada somente por fixture ou script sintético versionado. Não copiar dump de pré-produção neste gate.

A fixture representativa deve incluir apenas os contratos necessários para provar:

- upgrade sem perda de identidade de eventos;
- ausência de vínculo funcional de carteira em eventos globais;
- preservação das colunas canônicas de fonte e evento;
- ausência de duplicação após reexecução;
- chegada ao `head` sem intervenção manual.

Depois execute:

```powershell
python -m alembic upgrade head
python -m alembic current
python -m alembic check
```

## 4. Reexecução

Repita `upgrade head`, `current` e `check` nos dois bancos. A segunda execução deve ser idempotente e não alterar contagens estruturais.

## 5. Limpeza

```powershell
docker compose exec db psql -U sgi -d postgres `
  -v ON_ERROR_STOP=1 `
  -c "DROP DATABASE IF EXISTS $EmptyDb;"

docker compose exec db psql -U sgi -d postgres `
  -v ON_ERROR_STOP=1 `
  -c "DROP DATABASE IF EXISTS $LegacyDb;"
```

## Critérios de aprovação

- os dois bancos alcançam `head`;
- `alembic current` retorna a revisão esperada;
- `alembic check` não aponta novas operações pendentes;
- reexecução não produz mudanças adicionais;
- nenhum dado real ou provider externo é acessado;
- evidência registra branch, SHA, comandos e resultados.

## Proibições

Não usar neste roteiro:

- banco `sgi` principal;
- dumps de pré-produção ou produção;
- seed real;
- BRAPI, Yahoo ou B3 em modo operacional;
- migrations de contração sem fixture descartável específica;
- rebuild ou importação de carteira.
