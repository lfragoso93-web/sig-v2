# Auditoria da fonte de eventos monetários do Tesouro

> Atualizado em 11/10/2026. Escopo estritamente read-only da #149.

## Atualizacao de evidencia oficial — 17/10/2026

O regulamento oficial da B3 para o Tesouro Direto acrescenta a regra que faltava
para elegibilidade: conforme o item 95, tem direito ao evento o investidor com o
título disponível na Conta de Custódia na manhã do pagamento, antes de qualquer
depósito ou transferência nesse dia. Isso define a condição operacional, mas
não fornece a quantidade de abertura por investidor/carteira. O histórico diário
de transações do SGI sozinho não prova movimentos intradiários, transferências
ou disponibilidade operacional da custódia; é necessária posição/atividade de
custódia por conta e evento.

O item 97 atribui ao Agente de Custódia o repasse e a responsabilidade pelos
impostos. Os itens 100–101 dizem que o agente consulta saldos, movimentações e
preços de aquisição para esse cálculo. Portanto, o CSV agregado de cupom não
determina um `taxable_income_per_unit` universal: o componente tributável e o
IRRF devem vir de evidência fiscal por lote/conta ou de método oficial
documentado, sem derivação mecânica do valor bruto.

Fontes primárias:

- [Regulamento do Tesouro Direto publicado pela B3 (itens 94–101)](https://www.b3.com.br/data/files/E5/23/D0/8E/03A498101DBF7498AC094EA8/Regulamento%20TD%20Publicado%20no%20Site%20.11.07.2023.pdf)
- [Recurso oficial de Pagamento de Cupom de Juros do Tesouro Transparente](https://www.tesourotransparente.gov.br/ckan/dataset/f30db6e4-6123-416c-b094-be8dfc823601/resource/b04812f4-c453-4298-a12e-0ad190998243)

Conclusão atualizada: a **regra** de elegibilidade está identificada; seguem
pendentes evidência da posição disponível por carteira/conta na manhã do
pagamento e a base tributável por lote. A implementação não requer certificação
de runtime por iteração; eventual promoção/uso amplo de dados reais continua
sujeita ao gate operacional separado da identidade exata. Não houve consulta
ao banco, gravação financeira, alteração de código ou promoção nesta pesquisa.

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

A regra oficial de elegibilidade já foi localizada. Antes de qualquer plano de
ingestão, falta evidência de posição disponível por conta/carteira na manhã de
cada pagamento, incluindo liquidações e transferências aplicáveis. Também falta
base tributável/IRRF por lote em extrato do custodiante ou método oficial
documentado. O componente tributável permanece explícito e não pode ser
derivado mecanicamente do PU bruto.
