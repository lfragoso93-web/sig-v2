# Validação Alembic com reset do banco local de testes

Este roteiro é válido somente quando o operador confirmou explicitamente que o banco PostgreSQL local do Compose é descartável e pode ser apagado.

## Escopo

- remover o volume PostgreSQL local do projeto;
- recriar o banco `sgi` vazio;
- executar `alembic upgrade head`;
- validar `alembic current` e `alembic check`;
- repetir a sequência para comprovar idempotência;
- não executar seed, providers externos, rebuild ou importação de carteira.

## Pré-condições

- branch `stable-15jun` sincronizada;
- working tree limpa;
- autorização explícita para apagar o banco local de testes;
- Docker Desktop disponível;
- nenhum dado local precisa ser preservado;
- Issue #227 continua bloqueando operações reais.

## 1. Confirmar identidade

```powershell
$CommitSha = (git rev-parse HEAD).Trim().ToLowerInvariant()
$CommitSha
git status --short
```

## 2. Derrubar containers e apagar o volume PostgreSQL local

> Este comando apaga o banco local do Compose.

```powershell
docker compose down -v
```

## 3. Recriar somente a infraestrutura necessária

```powershell
docker compose up -d db redis

docker compose ps
```

Aguarde até `db` e `redis` aparecerem como `Healthy`.

## 4. Primeira execução Alembic

```powershell
docker compose run --rm backend `
  python -m alembic upgrade head

docker compose run --rm backend `
  python -m alembic current

docker compose run --rm backend `
  python -m alembic check
```

## 5. Confirmar revisão persistida

```powershell
docker compose exec db psql -U sgi -d sgi `
  -v ON_ERROR_STOP=1 `
  -c "SELECT version_num FROM alembic_version;"
```

## 6. Segunda execução idempotente

```powershell
docker compose run --rm backend `
  python -m alembic upgrade head

docker compose run --rm backend `
  python -m alembic current

docker compose run --rm backend `
  python -m alembic check
```

A segunda execução não deve criar novas migrations, alterar a revisão ou falhar.

## 7. Verificação final

```powershell
git status --short
git diff --check
```

## Critérios de aprovação

- banco vazio alcança `head`;
- `alembic current` aponta para a revisão esperada;
- `alembic check` informa ausência de novas operações;
- a segunda execução é idempotente;
- `alembic_version` contém uma única revisão válida;
- nenhum provider, seed, rebuild ou dado externo é acessado;
- working tree permanece limpa.

## Proibições

Não executar durante este gate:

- BRAPI, Yahoo, B3 ou Tesouro em modo operacional;
- seed de ativos, preços, Proventos ou eventos corporativos;
- rebuild de mercado ou carteira;
- importação CSV real;
- restauração de dump externo;
- qualquer comando equivalente em pré-produção ou produção.
