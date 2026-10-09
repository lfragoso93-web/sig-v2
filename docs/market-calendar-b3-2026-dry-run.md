# Relatório dry-run — calendário B3 2026

Data da verificação: 09/10/2026.

Fonte anual oficial: [Calendário de negociação da B3: confira o funcionamento
da bolsa em 2026](https://www.b3.com.br/pt_br/noticias/calendario-de-negociacao-da-b3-confira-o-funcionamento-da-bolsa-em-2026.htm),
publicado em 09/01/2026.

A publicação declara que a programação cobre negociação, registro,
compensação, liquidação e depósito centralizado em todos os segmentos da B3 e
lista o Tesouro Direto entre as operações suspensas nos feriados indicados.
O aviso específico de Corpus Christi, publicado em 29/05/2026, confirma que em
04/06 não há negociação nem confirmação de investimentos no Tesouro Direto.

## Resultado do extrator read-only

O texto publicado foi fornecido ao extrator
`extract_b3_annual_calendar_dry_run` para o mercado
`TESOURO_DIRETO_STANDARD`.

```text
schema_version: b3-market-calendar-dry-run.v1
dry_run: true
database_writes_executed: 0
complete_daily_coverage: false
```

Datas explicitamente fechadas extraídas:

```text
2026-01-01
2026-02-16
2026-02-17
2026-04-03
2026-04-21
2026-05-01
2026-06-04
2026-09-07
2026-10-12
2026-11-02
2026-11-20
2026-12-24
2026-12-25
2026-12-31
```

Data com horário especial, que não é um fato de fechamento:

```text
2026-02-18
```

A referência a 09/07 foi corretamente excluída: a publicação informa
funcionamento normal nesse feriado.

## Decisão

O relatório é evidência de forma e proveniência da fonte, não uma carga do
calendário canônico. A tabela `market_calendar_days` continua sem fatos novos.
Ainda falta certificar a regra que permite preencher cada data ordinária do ano
e consolidar avisos B3 posteriores; portanto, não há cobertura diária para
aplicar D+2 no banco.
