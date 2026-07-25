# Limpeza transacional dos legados Tesouro Educa+

## Escopo

A CLI `python -m app.cli.cleanup_treasury_legacy_assets` trata exclusivamente os pares aprovados:

- `4742 / tesouro-educa-15122030` → alias de `4810 / tesouro-educa-mais-2030`;
- `4747 / tesouro-educa-15122031` → alias de `4823 / tesouro-educa-mais-2031`.

Nenhum outro ativo, preço ou alias faz parte deste mecanismo.

## Modos

Sem argumentos, a CLI executa **dry-run**. Ela abre conexão, inspeciona e valida o estado, emite JSON `treasury-legacy-cleanup.v1` e encerra sem `INSERT` ou `DELETE`.

A escrita exige `--apply`. Essa flag não deve ser usada sem autorização humana explícita registrada na Issue #158.

## Pré-condições fechadas

A operação rejeita o estado quando qualquer uma destas condições divergir:

- IDs, tickers ou tipo `TESOURO_DIRETO` dos quatro ativos;
- alias legado já existente ou conflitante;
- referência funcional dos legados em tabelas conhecidas;
- quantidade diferente de dois preços `brapi_treasury` por legado;
- campos OHLCV presentes nos quatro registros incompatíveis;
- `close` diferente de R$ 3.518,20 para `4742` ou R$ 3.769,72 para `4747`;
- menos de 743 preços `tesouro_transparente` por ativo canônico;
- preço órfão ou duplicidade por `(asset_id, timestamp)`.

## Transação

No modo de aplicação, a mesma transação:

1. cria os dois aliases canônicos;
2. remove exatamente quatro preços `brapi_treasury`;
3. remove exatamente dois ativos legados;
4. executa as pós-validações;
5. faz commit somente se todas as verificações forem aprovadas.

Qualquer exceção, contagem divergente ou falha de pós-condição provoca rollback integral pela CLI.

A segunda execução válida retorna `status=already-applied` e não escreve novamente.

## Saída auditável

O JSON informa:

- `schema_version`;
- `mode` (`dry-run` ou `apply`);
- `status`;
- timestamps de início e fim;
- snapshot anterior;
- snapshot posterior quando aplicável;
- contagens planejadas e aplicadas.

## Validação controlada

Somente PostgreSQL e Redis devem permanecer ativos. Backend e frontend não precisam ser iniciados.

```powershell
# Ajuda não destrutiva
docker compose run --rm --no-deps backend `
  python -m app.cli.cleanup_treasury_legacy_assets --help

# Testes sem acesso ao banco real
docker compose run --rm --no-deps backend `
  pytest -q tests/test_treasury_legacy_cleanup.py tests/test_treasury_cli_help.py

# Compilação
docker compose run --rm --no-deps backend `
  python -m compileall -q app/cli/cleanup_treasury_legacy_assets.py app/services/treasury_legacy_cleanup.py

# Dry-run no banco configurado; não usar --apply
docker compose run --rm --no-deps backend `
  python -m app.cli.cleanup_treasury_legacy_assets
```

O comando com `--apply` permanece proibido até autorização explícita.
