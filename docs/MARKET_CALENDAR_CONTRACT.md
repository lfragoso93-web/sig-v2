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

### Hierarquia certificada para 2026

O artefato anual a revisar é o [Ofício Circular B3 041/2026-VNC — errata do
calendário de feriados](https://www.b3.com.br/data/files/20/57/01/AA/06A1F910ADC36BE9AC094EA8/OC%20041-2026-VNC%20ERRATA%20-%20CALENDARIO%20DE%20FERIADOS%20EM%202026_PT.pdf).
Ele relaciona os feriados nacionais e pontos facultativos de 2026, estabelece
que não há negociação e confirmação de investimentos do Tesouro Direto nessas
datas e explicita funcionamento normal em 09/07.

O portal de [avisos do Tesouro Direto](https://tesourodireto.com.br/como-investir/avisos)
é a fonte complementar para interrupções operacionais posteriores. Um aviso
intradiário, atraso de precificação ou indisponibilidade temporária não altera
sozinho `is_business_day`: somente um documento que estabeleça suspensão do dia
ou mudança de liquidação permite alterar um fato diário já revisado.

Assim, a fonte anual e os avisos não autorizam inferir uma cobertura diária
completa sem um artefato revisado que declare a regra dos dias ordinários. O
planejador de promoção continua bloqueando essa lacuna.

## Plano de promoção sem escrita

`python -m app.cli.plan_market_calendar_promotion <candidate.json>` aceita
somente um candidato completo no schema `market-calendar-candidate.v1`. Cada
dia do ano deve ter `date`, `is_business_day` e referência a um documento-fonte
com SHA-256. A CLI não acessa o banco, não busca a internet e retorna
`database_writes_executed=0`.

O plano falha fechado para cobertura incompleta, data duplicada, dia fora do
ano ou referência de fonte desconhecida. Um plano promovível apenas comprova
que o candidato revisado tem cobertura e proveniência suficientes; ele não
executa inserção, upsert nem autoriza uma carga futura.

## Auditoria mensal da fonte

O scheduler pode executar a auditoria mensal no dia 1 às 08:15 de São Paulo,
somente quando `ENABLE_B3_MARKET_CALENDAR_MONTHLY_AUDIT=true`. A configuração
deve fornecer `B3_MARKET_CALENDAR_SOURCE_URL` (HTTPS em `www.b3.com.br`) e
`B3_MARKET_CALENDAR_SOURCE_YEAR`. O job usa lease Redis, limita a resposta HTTP
e registra hash e contagens do relatório; não escreve no banco. A URL/ano devem
ser renovados quando a B3 publicar o calendário anual seguinte.

Os campos `market_calendar.b3_source_url` e
`market_calendar.b3_source_year` já aparecem em **Configurações > Avançado >
Painel Admin > Config. do sistema** para o SuperAdmin. Em instalação nova,
iniciam com a publicação oficial de 2026; valores não vazios têm precedência
sobre o `.env`. URL ou ano inválidos interrompem a auditoria sem alterar fatos
do calendário.

`TESOURO_DIRETO_STANDARD` também não representa produtos com liquidação
instantânea ou disponibilidade 24x7, como modalidades especiais do Tesouro
Reserva. Esses produtos exigem mercado/regra próprios antes de usar o mesmo
calendário ou a convenção conservadora D+2.
