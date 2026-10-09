# Contrato do calendário de mercado

O componente canônico `MarketCalendarDay` registra fatos certificados por dia e
mercado. A leitura financeira usa esses fatos pelo serviço
`add_certified_business_days`; ela falha quando a cobertura diária é
incompleta, em vez de supor que um dia sem registro seja útil.

## Fonte e ingestão inicial da B3

Para `TESOURO_DIRETO_STANDARD`, o calendário anual oficial da B3 é uma fonte
de partida. O extrator `extract_b3_annual_calendar_dry_run` é estritamente
read-only: recebe o texto já obtido da fonte oficial, extrai apenas datas que
o texto descreve explicitamente como fechadas, separa horários especiais e
produz um relatório com `database_writes_executed=0`.

Ele não completa os demais dias do ano e não pode certificar a tabela sozinho.
Antes de persistir fatos, a carga deve revisar a fonte anual, comunicações B3
posteriores que a alterem e a aplicabilidade ao Tesouro. Avisos específicos
têm precedência sobre a publicação anual.

## Auditoria mensal da fonte

O scheduler pode executar a auditoria mensal no dia 1 às 08:15 de São Paulo,
somente quando `ENABLE_B3_MARKET_CALENDAR_MONTHLY_AUDIT=true`. A configuração
deve fornecer `B3_MARKET_CALENDAR_SOURCE_URL` (HTTPS em `www.b3.com.br`) e
`B3_MARKET_CALENDAR_SOURCE_YEAR`. O job usa lease Redis, limita a resposta HTTP
e registra hash e contagens do relatório; não escreve no banco. A URL/ano devem
ser renovados quando a B3 publicar o calendário anual seguinte.

`TESOURO_DIRETO_STANDARD` também não representa produtos com liquidação
instantânea ou disponibilidade 24x7, como modalidades especiais do Tesouro
Reserva. Esses produtos exigem mercado/regra próprios antes de usar o mesmo
calendário ou a convenção conservadora D+2.
