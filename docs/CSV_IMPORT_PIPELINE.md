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

Após uma importação bem-sucedida, o sistema identifica a primeira transação da carteira, remove os snapshots afetados, reconstrói todos os dias corridos até hoje e invalida novamente os caches financeiros.

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

## Cripto e cobertura de mercado

O preflight e o gravador canonico permitem registrar compra/venda CRIPTO quando
o ticker existe no catalogo persistido, mesmo que o historico esteja incompleto
ou com status `HISTORY_END_UNAVAILABLE`. A transacao contem quantidade, preco e
data informados pelo usuario; cobertura de mercado e uma dimensao separada e
continua visivel para valuation/readiness. O SGI nao cria ticker CRIPTO ausente
do catalogo nem consulta provider durante a importacao.

Para as demais classes listadas em `PRICE_HISTORY_REQUIRED_TYPES`, o preflight
ainda exige ativo e precos persistidos. Falhas em linhas desses tipos precisam
ser diagnosticadas pelo relatorio do dry-run (ticker/tipo/erro), pois nao sao
explicadas pelo gate especifico de cripto.

## Formatos de Arquivo e Provedores Suportados

O pipeline de importação aceita múltiplos formatos de arquivo via endpoint unificado `/portfolios/{id}/import-csv` e `/portfolios/{id}/import-transactions`:

1. **Modelo Canônico SGI**:
   - Arquivos `.csv` ou `.xlsx` com as 9 colunas canônicas (`ticker, asset_type, operation, quantity, price, date, fees, currency, notes`) e suporte a colunas opcionais de renda fixa.

2. **Área do Investidor B3**:
   - Arquivos `.xlsx`, `.pdf` ou `.csv` exportados diretamente da Área do Investidor B3 (incluindo classificação precisa de incorporadoras `^[A-Z]{4}[345678]$` como `ACAO`, `AREA11` como `ETF_NACIONAL` e `advisories` não bloqueantes para `"Atualização"` a `R$ 0,01`).
   - Suporte a extratos de **Movimentação** e relatórios de **Negociação**.
   - Mapeamento automático de tipos de ativos (`ACAO`, `FII`, `BDR`, `TESOURO_DIRETO`, `RENDA_FIXA`).
   - Normalização de títulos do Tesouro Direto com descarte de sufixos de corretoras nos relatórios PDF.
   - Mapeamento inteligente de operações: `APLICAÇÃO` e compras como `buy`, `RESGATE`, `RESGATE ANTECIPADO` e vendas como `sell`.
   - Incorporação de eventos corporativos de custódia que alteram quantidade de cotas (Desdobro, Bonificação em Ativos, Atualização e Fração em Ativos) para consistência no inventário de vendas, com segregação de débitos de frações órfãs sem saldo prévio em carteira.
   - Segregação de débitos de `Fração em Ativos` em ativos que sofreram `Grupamento`, evitando dupla dedução com o motor canônico de eventos corporativos e mantendo a fração pendente até liquidação em leilão.
   - Desambiguação de retornos de empréstimo de ativos (BTC) frente a compras genuínas em bolsa: a devolução de custódia só é segregada quando correspondida por encerramento explícito de contrato (`Credito Empréstimo` em janela de liquidação), preservando compras reais realizadas enquanto há contratos BTC ativos.
   - Segregação automática de proventos e eventos em dinheiro (dividendos, JCP, rendimentos) e transferências sem liquidação de mercado.
   - Validação de saldo de vendas no pré-vôo e no `transaction_write_service` com tolerância de ponto flutuante (`math.isclose` 1e-7) para liquidação exata de parcelas fracionárias.

3. **Notas de Corretagem (Padrão Sinacor)**:
   - Arquivos `.pdf` e texto estruturado de notas de corretagem padrão Sinacor (Banco Inter, XP Investimentos, Clear, BTG Pactual, Rico, NuInvest, etc.).
   - Extração do pregão (`Data pregão`), número da nota e instituição corretora.
   - Detecção de linhas de operação no formato Bovespa à vista e fracionário (`[1-BOVESPA] [C|V] [VISTA|FRACIONARIO] <ESPECIFICAÇÃO> <QUANTIDADE> <PREÇO> <VALOR TOTAL>`).
   - Rateio proporcional dos custos e taxas operacionais (`Taxa de liquidação`, `Emolumentos`, `Corretagem`, `ISS`, `Total custos / despesas`) ponderados pelo volume de cada ativo executado.
