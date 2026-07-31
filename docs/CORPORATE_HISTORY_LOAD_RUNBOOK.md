# Carga histórica de eventos corporativos

## Escopo

A carga reconstrói exclusivamente o catálogo global `corporate_events` para
ações, BDRs e ETFs nacionais. Ela não altera transações, posições, snapshots,
proventos financeiros ou carteiras.

Janela padrão:

```text
2000-01-01 até a data da execução
```

## Pré-condições

1. branch e SHA operacionais registrados;
2. backup aprovado;
3. migration `20260731_corp_event_catalog` aplicada em janela controlada;
4. token BRAPI Pro validado;
5. nenhuma outra carga corporativa em execução;
6. diretório de evidências fora de áreas públicas da aplicação.

## Dry-run obrigatório

```powershell
python -m app.cli.load_corporate_history `
  --run-id 20260731-190000 `
  --date-from 2000-01-01 `
  --date-to 2026-07-31 `
  --output ../artifacts/corporate-actions/dry-run.json
```

Dry-run é o padrão e sempre termina em rollback. O relatório preserva estado
inicial, estado projetado, ativos processados, eventos novos, reconciliação e
erros por ticker.

## Critérios de aprovação do dry-run

- `ok=true`;
- `transaction_state=dry_run_rolled_back`;
- nenhum erro de provider ou normalização;
- nenhum `CONFLICT` sem análise registrada;
- nenhum evento desconhecido aplicado;
- quantidades e fontes compatíveis com a auditoria BRAPI Pro;
- relatório sem credenciais.

## Aplicação controlada

A aplicação exige dois parâmetros adicionais e confirmação humana explícita:

```powershell
python -m app.cli.load_corporate_history `
  --run-id 20260731-193000 `
  --date-from 2000-01-01 `
  --date-to 2026-07-31 `
  --apply `
  --authorization I-AUTHORIZE-CORPORATE-HISTORY `
  --output ../artifacts/corporate-actions/apply.json
```

Qualquer falha de ativo é isolada por savepoint, registrada e torna o resultado
global inválido. Nesse caso, a transação inteira é revertida. O advisory lock
transacional impede duas cargas simultâneas.

## Prova de idempotência

Após a aplicação aprovada:

1. executar um segundo dry-run com a mesma janela e SHA;
2. exigir `events_created=0`;
3. exigir contagens e estados de reconciliação estáveis;
4. comparar os artefatos sem consultar ou modificar o banco;
5. registrar a evidência na Issue #129.

## Ativação incremental posterior

O scheduler não executa a carga histórica. Depois da migration, aplicação
controlada, prova de idempotência e aprovação operacional, habilitar somente a
coleta incremental:

```dotenv
CORPORATE_EVENTS_SCHEDULER_ENABLED=true
CORPORATE_EVENTS_INCREMENTAL_LOOKBACK_DAYS=45
```

Após reiniciar o backend, confirmar o job
`sync_corporate_events_incremental` às 18:35 em dias úteis. O ciclo usa o mesmo
advisory lock da carga histórica, savepoint por ativo e registra contagens de
ativos, eventos, reconciliação, conflitos e falhas. Lock ocupado resulta em
skip observável; não há aplicação automática de evento em revisão.

Para rollback operacional, retornar a flag a `false` e reiniciar o backend. Os
eventos já catalogados permanecem preservados para auditoria.

Eventos `UNRECONCILED`, `CONFLICT` ou de tipo complexo devem ser tratados pela
API administrativa de revisão. Aprovação exige SuperAdmin e justificativa; uma
decisão final fica protegida contra sobrescrita pela reconciliação incremental.

## Abortos obrigatórios

- migration ausente;
- lock indisponível;
- autenticação ou permissão BRAPI recusada;
- rótulo corporativo desconhecido;
- divergência de fonte não revisada;
- tentativa de `--apply` sem a frase exata de autorização;
- qualquer tentativa de executar a carga pelo scheduler antes da aprovação.
