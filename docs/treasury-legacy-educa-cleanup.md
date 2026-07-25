# Limpeza transacional dos legados Tesouro Educa+

## Escopo

A CLI `python -m app.cli.cleanup_treasury_legacy_assets` trata exclusivamente os pares aprovados:

- `4742 / tesouro-educa-15122030` → alias de `4810 / tesouro-educa-mais-2030`;
- `4747 / tesouro-educa-15122031` → alias de `4823 / tesouro-educa-mais-2031`.

Nenhum outro ativo, preço ou alias faz parte deste mecanismo.

## Modos e autorização

Sem argumentos, a CLI executa **dry-run**. Ela abre conexão, inspeciona e valida o estado, emite JSON `treasury-legacy-cleanup.v1` e encerra sem `INSERT` ou `DELETE`.

A escrita exige simultaneamente:

```text
--apply --authorization ISSUE-158-APPROVED
```

A confirmação é validada antes da criação da engine. `--apply` isolado, token incorreto ou `--authorization` sem `--apply` encerram com código `2` e não acessam o banco.

O token é uma trava técnica adicional, não uma autorização autônoma. Ele só pode ser usado após autorização humana explícita registrada na Issue #158, com referência ao dry-run aprovado e ao SHA executado.

## Pré-condições fechadas

A operação rejeita o estado quando qualquer uma destas condições divergir:

- IDs, tickers ou tipo `TESOURO_DIRETO` dos quatro ativos;
- alias legado já existente ou conflitante;
- referência funcional dos legados em tabelas conhecidas;
- quantidade diferente de dois preços `brapi_treasury` por legado;
- campos OHLCV presentes nos quatro registros incompatíveis;
- conjunto de `close` diferente de R$ 3.518,20 e R$ 3.522,89 para `4742`;
- conjunto de `close` diferente de R$ 3.769,72 e R$ 3.777,79 para `4747`;
- menos de 743 preços `tesouro_transparente` por ativo canônico;
- preço órfão ou duplicidade por `(asset_id, timestamp)`.

Os quatro preços legados foram confirmados no PostgreSQL real em 25/07/2026. Como cada legado deve possuir exatamente duas linhas, sem OHLCV, a validação simultânea de `min_close` e `max_close` fecha o conjunto aceito sem permitir valores adicionais.

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

## Gate operacional antes de autorizar escrita

Todos os itens abaixo devem estar registrados na Issue #158:

1. branch `stable-15jun` sincronizada e SHA completo registrado;
2. imagem backend reconstruída a partir do mesmo SHA;
3. `compileall` aprovado;
4. testes direcionados aprovados;
5. dry-run imediatamente anterior com `status=validated` e exit code `0`;
6. ausência de scheduler, coleta, seed, importação ou rebuild concorrente;
7. snapshot SQL dos quatro ativos, aliases, referências funcionais e preços;
8. autorização humana explícita para uma única execução;
9. operador e horário planejado registrados.

Qualquer mudança no SHA, no banco ou no estado operacional invalida a autorização e exige novo dry-run.

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

## Comando de aplicação — bloqueado até autorização

O comando operacional preparado é:

```powershell
docker compose run --rm --no-deps backend `
  python -m app.cli.cleanup_treasury_legacy_assets `
  --apply `
  --authorization ISSUE-158-APPROVED
```

Não executar enquanto a Issue #158 não contiver autorização explícita e vigente.

## Verificação pós-operação

Após uma aplicação autorizada, executar imediatamente:

```powershell
docker compose run --rm --no-deps backend `
  python -m app.cli.cleanup_treasury_legacy_assets
```

O resultado esperado é `status=already-applied`, exit code `0`, dois aliases apontando para os ativos canônicos, zero preços ligados aos IDs legados e integridade sem órfãos ou duplicidades.

Se o comando de aplicação retornar código diferente de `0`, nenhuma correção manual deve ser feita. A transação deve permanecer revertida e a evidência completa deve ser registrada na Issue #158 antes de nova análise.
