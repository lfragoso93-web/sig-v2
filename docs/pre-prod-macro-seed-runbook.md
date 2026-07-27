# Seed isolado de benchmarks macroeconômicos

## Escopo

Este runbook cobre exclusivamente as séries persistidas em `rate_history` para CDI, SELIC, IPCA e IGPM. O estágio não executa B3/COTAHIST, Tesouro Direto, câmbio, proventos, importação CSV, posições, snapshots ou `full_market_rebuild`.

Contrato principal: `pre-prod-macro-seed.v1`.

Contrato da comparação offline: `pre-prod-macro-seed-compare.v1`.

## Entradas operacionais

Seed isolado:

```powershell
$RunId = Get-Date -Format "yyyyMMdd-HHmmss"
$CommitSha = (git rev-parse HEAD).Trim()

.\scripts\pre_prod_macro_seed.ps1 `
    -RunId $RunId `
    -Branch "stable-15jun" `
    -CommitSha $CommitSha
```

Cada execução preserva:

```text
artifacts/pre-prod-rebuild/<run-id>/macro-seed.json
```

## Prova de idempotência

A comparação exige duas execuções bem-sucedidas do mesmo commit. O estado final deve permanecer estável, a segunda execução não pode aumentar `after.total_rows`, e a integridade deve permanecer sem duplicidades ou indicadores não suportados.

O campo `imported` registra linhas submetidas ao UPSERT e pode incluir conflitos atualizados. Portanto, novas linhas são medidas pelo delta real entre `before.total_rows` e `after.total_rows` da segunda execução.

Persistência oficial da comparação:

```powershell
$CompareRunId = Get-Date -Format "yyyyMMdd-HHmmss"

.\scripts\compare_pre_prod_macro_seed.ps1 `
    -FirstEvidence ".\artifacts\pre-prod-rebuild\<primeiro-run-id>\macro-seed.json" `
    -SecondEvidence ".\artifacts\pre-prod-rebuild\<segundo-run-id>\macro-seed.json" `
    -RunId $CompareRunId
```

Artefato produzido:

```text
artifacts/pre-prod-rebuild/<compare-run-id>/macro-seed-compare.json
```

O wrapper recusa sobrescrita, aceita evidências UTF-8 com ou sem BOM, valida `schema_version` e retorna falha quando `ok` não é verdadeiro.

## Evidência validada

Em 25/07/2026, as execuções `20260725-231557` e `20260725-231604`, ambas vinculadas ao commit `181597c21f9769896cd7bc74dfdae929f2a0b3c0`, foram comparadas com sucesso:

- mesmo commit;
- estado final estável;
- zero novas linhas na segunda execução;
- zero duplicidades;
- zero indicadores não suportados;
- `ok=true`.

## Critérios de aborto

Interromper o estágio diante de qualquer uma destas condições:

- branch diferente de `stable-15jun`;
- SHA inválido ou divergente do HEAD;
- advisory lock indisponível;
- erro de coleta, persistência ou inspeção;
- duplicidades em `rate_history`;
- indicador não suportado;
- crescimento de linhas na segunda execução de idempotência;
- estado final divergente entre as duas execuções;
- evidência ausente, inválida ou já existente no destino.

## Próximo domínio

Câmbio deve usar estágio, contrato, lock, transação, evidência e comparação próprios. Não deve ser acoplado novamente ao seed de benchmarks.
