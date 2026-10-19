# Contrato proposto para eventos corporativos complexos

Data: 19/10/2026  
Status: classificador B3 e projetor puro em memoria implementados parcialmente; sem persistencia, integracao financeira ou alteracao de dados.

## Contexto verificado

O motor atual normaliza desdobramento, grupamento, bonificação e subscrição.
O projetor canônico aplica fatores de quantidade e preserva custo total nos
eventos suportados. Ele não implementa transformação de ativos de destino nem
liquidação monetária de resgate.

O primeiro bloco técnico acrescentou `ComplexCorporateActionKind`,
`B3ComplexCorporateActionCandidate` e
`normalize_b3_complex_corporate_action_candidates()` em
`corporate_action_engine.py`. O classificador identifica incorporação, cisão e
resgate conhecidos da B3, exige ticker/ISIN de origem e data de direito e
agrupa várias linhas de ativo emitido para a mesma ação. Para incorporação/cisão
exige ao menos um ISIN de destino. O DTO sempre declara `projectable=false`,
`quantity_factor=None` e `effective_date=None`; não está ligado à persistência,
ao leitor nem ao projetor.

`corporate_events` já contém `destination_asset_id`, `destination_ticker`,
`destination_isin_code`, `quantity_factor`, `destination_cost_allocation`,
`cash_component`, `record_date` e `effective_date`. Esses campos não constituem
por si só uma regra de domínio: há apenas um destino e o projetor não os usa
para aplicar incorporação/cisão/resgate.

O fluxo `ticker_change_processor` é outro contrato: resolve uma mudança de
símbolo durante importação CSV e pode acrescentar venda/compra sintéticas à
tabela `transactions`. Ele é portfolio-scoped e não é um processador global de
evento do emissor. Não deve ser chamado automaticamente para incorporação ou
cisão.

## Tipos e requisitos factuais

| Classe econômica | Efeito a modelar | Evidência mínima antes de projetar |
|---|---|---|
| Incorporação/troca de ativo | extingue origem e entrega um ou mais ativos destino | ISIN da origem e de cada destino, relação de conversão, data efetiva e documento do emissor/B3 |
| Cisão com entrega de ativo | mantém ou reduz origem e entrega um ou mais ativos destino | ISINs, quantidades/relações por destino, alocação de custo total e data efetiva |
| Resgate total em dinheiro | extingue quantidade e reconhece fluxo monetário/realização | quantidade elegível, valor bruto por unidade ou montante oficial, data de pagamento, custos e tratamento fiscal aplicável |
| Resgate parcial em dinheiro | reduz quantidade e reconhece fluxo monetário/realização | todos os itens anteriores, mais quantidade ou proporção resgatada |

Labels como `INCORPORACAO`, `CIS RED CAP` ou `RESG TOTAL RV` não definem
sozinhos o fator de conversão, ativo destino, preço de resgate ou alocação de
custo. O número `100` desses cinco registros BRAPI auditados não é um
multiplicador utilizável.

## Contrato de persistência proposto

1. Preservar cada fato de origem com `source_provider`, identidade e payload/hash.
2. Manter a ação global ligada ao ativo de origem (`portfolio_id=NULL`).
3. Representar cada destino como uma perna tipada, identificada por asset/ISIN,
   relação de conversão e parcela de custo. Um único campo de destino não cobre
   cisões com mais de um beneficiário; preferir tabela de pernas em vez de
   sobrecarregar `raw_metadata` ou criar várias ações economicamente duplicadas.
4. Validar `effective_date` separadamente do anúncio, deliberação, record date,
   ex-date e último dia com direito.
5. Para transformação sem caixa, exigir que a soma das alocações de custo das
   pernas de destino e da origem residual preserve 100% do custo anterior.
6. Para dinheiro, persistir valor e tratamento somente com evidência explícita;
   projetar caixa/realização pelo contrato financeiro canônico, sem criar valor
   a partir de fator percentual nem alterar transações históricas.
7. Reconciliar e executar dry-run por evento. Eventos sem todos os campos ficam
   `UNRECONCILED`/fora da projeção; conflito factual fica `CONFLICT`.

## Projeção e invariantes

- A posição antes da data efetiva é calculada somente pelo ledger persistido.
- O evento transforma a posição em cada carteira elegível; não cria uma
  transação histórica para fingir que a operação foi feita pelo usuário.
- A quantidade final deve seguir a relação oficial por perna e a política
  explícita para frações.
- Em transformações não monetárias, custo total deve ser conservado e repartido
  por alocação documentada; não inferir preço médio de mercado para preencher
  custo.
- Resgate monetário permanece não projetável até haver quantidade e valor
  oficiais conciliados e um contrato definido para fluxo e resultado realizado.
- Snapshots/cache são invalidados e reconstruídos somente após reconciliação
  validada, backup e preflight das carteiras impactadas.

## Sequência de implementação

1. DTO/enum e classificador candidato B3: concluído. O classificador falha
   fechado para classe/data/destino ausentes, mas ainda não demonstra relação de
   conversão nem autoriza projeção.
2. Contrato em memoria de pernas de destino: concluido. Cada perna exige ISIN,
   fator positivo explicito e alocacao de custo entre zero e um; a origem tambem
   tem fator e alocacao explicitos. A soma das alocacoes deve ser exatamente um.
   Ainda falta decidir e migrar a representacao persistida multi-perna.
3. Projetor puro nao monetario: concluido para incorporacoes e cisoes. Recebe
   somente conversoes ja resolvidas, valida ISINs, fatores e conservacao do
   custo, e devolve origem residual e destinos sem precos de mercado. Nao le
   payload de provedor, nao reconcilia candidatos e nao grava ledger/banco.
4. Integrar leitor, posições, custo, realizações, snapshots, resumo e IRPF,
   mantendo desconhecidos fora da projeção.
5. Tratar resgates monetários em bloco separado, após definir a fronteira entre
   fluxo de caixa, transações e resultado realizado.
6. Validar com fixtures oficiais sanitizadas e casos de uma/mais carteiras,
   execução idempotente, frações e restart; só então planejar promoção de
   eventos reais por identidade e data.

## Fora do escopo deste desenho

- Não reclassifica nem reconcilia IDs 6, 19, 64, 97 ou 111.
- Não modifica `transactions`, posições, snapshots ou eventos no banco.
- Não muda o comportamento de `ticker_change_processor`.
- Não autoriza coleta ampla, seed, migration, reconstrução ou alteração da imagem.


## Publica��o no ambiente de testes - 19/10/2026

O c�digo foi publicado no commit `2e8b36bdb0cd4d534c4b61b58fa06d7f64e43754` e imagem `sha256:4e129ab9b32319c193ee9655cd43432b4bd400288f4c734fc504c0e377134cb7`. Apenas o servi�o backend foi recriado. O import do DTO e classificador foi confirmado no container; `/health=200`, PostgreSQL e Redis OK, Alembic `20261017_fixed_income_contracts (head)`. Frontend e cloudflared permaneceram ativos. `/ready=503`; nenhuma certificacao foi criada e nenhum dado financeiro foi escrito. Nenhum teste foi executado neste bloco.

## Projetor puro de pernas nao monetarias - 19/10/2026

`corporate_action_engine.py` agora contem `CorporateActionDestinationLeg`,
`ResolvedNonCashCorporateAction`, `NonCashCorporateActionProjection` e
`project_non_cash_corporate_action()`. Cada destino exige ISIN, fator quantitativo
explicito e parcela de custo; a origem recebe fator residual e parcela propria.
As parcelas devem somar exatamente 1. Incorporacao extingue quantidade e custo
da origem; cisao permite origem residual. O custo anterior e conservado sem
inferencia de preco de mercado.

O projetor rejeita resgates monetarios, campos incompletos, destinos duplicados
ou iguais a origem, alocacao invalida e fatores nao positivos nos destinos.
Candidatos B3 nao se tornam projetaveis automaticamente. O projetor nao consulta
nem modifica `corporate_events` ou `transactions` e nao integra posicoes ou
snapshots. Persistencia multi-perna, evidencia/reconciliacao e fracoes continuam
pendentes. Compilacao e `git diff --check` passaram; testes nao foram executados.
