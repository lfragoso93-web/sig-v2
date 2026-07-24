# Perfil seguro de alvo — limpeza real de pré-produção

## Contexto

A execução transacional originalmente validada na Issue #196 aceitava somente um banco PostgreSQL isolado. A Issue #199 autorizou uma janela real de pré-produção e identificou que a proteção anterior recusava corretamente origem e destino iguais.

Este documento registra a habilitação mínima e explícita do alvo real sem remover o perfil isolado.

## Marcadores suportados

A CLI `python -m app.cli.pre_prod_isolated_cleanup` aceita somente dois marcadores:

- `sgi-pre-prod-isolated`: exige que origem e destino tenham identidades diferentes;
- `sgi-pre-prod-real`: exige que origem e destino tenham exatamente a mesma identidade normalizada de host, porta e banco.

Qualquer outro marcador aborta antes da criação do engine e antes de qualquer escrita.

## Invariantes preservados

Os dois perfis continuam exigindo:

- branch `stable-15jun`;
- SHA completo idêntico ao plano;
- `run_id` válido;
- contrato `pre-prod-cleanup-execution.v1` em modo `plan`;
- checksums canônicos íntegros;
- confirmação composta exata;
- driver PostgreSQL síncrono;
- contagens iguais a `expected_rows_before` antes do primeiro `DELETE`;
- lock transacional;
- limpeza somente na ordem do plano;
- rollback integral em qualquer falha;
- publicação de evidências redigidas e sem sobrescrita;
- ausência de seed, coleta, importação ou rebuild no mesmo bloco.

## Confirmação composta

O formato permanece:

```text
CLEANUP <run-id> ON <database> AT <commit-sha> WITH <plan-sha256>
```

O nome do banco deve corresponder ao banco presente na URL de destino.

## Execução real

Para a pré-produção real, a origem e o destino devem apontar para a mesma URL PostgreSQL síncrona e o marcador deve ser:

```text
sgi-pre-prod-real
```

O parâmetro `--rehearsal-fail-after-table` permanece proibido na execução real.

## Segurança

O perfil real não transforma o marcador em um booleano genérico. Ele troca uma proteção por outra:

- o perfil isolado recusa origem igual ao destino;
- o perfil real recusa origem diferente do destino.

Assim, não é possível reutilizar acidentalmente a autorização real contra um banco descartável diferente, nem reutilizar a autorização isolada contra a origem.
