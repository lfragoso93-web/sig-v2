# Auditoria da fonte de eventos monetários do Tesouro

> Atualizado em 11/10/2026. Escopo estritamente read-only da #149.

## Fonte oficial encontrada

O conjunto `resgates-do-tesouro-direto`, publicado pelo Tesouro Transparente,
contém um recurso CSV de pagamentos de cupons. Seus campos observados são:

```text
Tipo Titulo
Vencimento do Titulo
Data Resgate
PU
Quantidade
Valor
```

O recurso comprova título, vencimento, data de pagamento, valor bruto unitário
e totais agregados. Ele não publica `record_date`, posição individual elegível
nem parcela tributável por unidade.

## Decisão fail-closed

O relatório `treasury-cash-event-source-audit.v1` classifica as linhas válidas
como fatos de fonte aceitos, mas mantém `promotable_events=0` e
`database_writes_executed=0`.

Sem uma regra oficial que determine a elegibilidade por carteira, o CSV não
autoriza criar `asset_dividends`, projetar direitos ou calcular IRRF. A
quantidade do arquivo é agregada para todo o programa e não substitui a posição
histórica do investidor.

## Execução

```powershell
cd backend
..\.venv\Scripts\python.exe -m app.cli.audit_treasury_cash_event_source
```

A CLI consulta somente o pacote CKAN e o recurso oficial mais recente. Não abre
sessão de banco, não recebe `--execute` e não possui caminho de persistência.

## Próxima evidência necessária

Antes de qualquer plano de ingestão, é necessário obter fonte oficial ou
evidência de custodiante/corretora que fixe a data de elegibilidade para cada
evento. O componente tributável por unidade também deve permanecer explícito;
não pode ser derivado mecanicamente do PU bruto.
