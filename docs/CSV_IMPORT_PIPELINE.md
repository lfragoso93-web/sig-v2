# Pipeline de importação CSV

## Fluxo

1. Upload e leitura do arquivo.
2. Validação estrutural e por linha.
3. Resolução de tickers antigos.
4. Dry-run com classificação em válidas, avisos e erros.
5. Confirmação do usuário.
6. Importação transacional.
7. Registro de aliases e eventos simples de renome.
8. Invalidação de caches.
9. Reconstrução de snapshots em segundo plano.

## Validação temporal de tickers

- Operações anteriores à data efetiva do renome aceitam o ticker antigo como alias histórico.
- Operações na data efetiva ou posteriores exigem o ticker atual.
- Sem data efetiva confiável, a linha permanece bloqueada.
- Falhas de rede ou payload inválido não interrompem o parser.

## Persistência

As transações históricas permanecem imutáveis. Quando aplicável, o sistema registra o ativo atual, o alias histórico e um evento `TICKER_CHANGE` idempotente.

## Rebuild de snapshots

Após uma importação bem-sucedida, o sistema identifica a primeira transação da carteira, remove os snapshots afetados, reconstrói todos os dias úteis até hoje e invalida novamente os caches financeiros.

O rebuild roda em segundo plano para não bloquear a resposta da importação.

## Idempotência

- Alias único por ticker antigo e tipo de ativo.
- Evento de troca de ticker com chave idempotente.
- Operações técnicas marcadas pelo evento.
- Reprocessamento sem duplicação de conversões.

## Testes mínimos

- CSV válido e inválido.
- Renome antes e depois da data efetiva.
- Falha do provedor externo.
- Venda parcial e venda total antes do renome.
- Rebuild a partir da primeira transação.
- Invalidação de caches.