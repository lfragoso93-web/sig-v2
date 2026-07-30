# Arquitetura canônica de Proventos

> Decisão arquitetural: 30/07/2026  
> Issue: #226  
> Estado: aprovada; migração incremental pendente

## Regra fundamental

Todo provento pertence exclusivamente a um ativo. A carteira não armazena uma
cópia do evento: ela consulta o catálogo global e calcula seu eventual direito
financeiro com base na posição histórica na data de direito.

## Modelo canônico

- `asset_dividends`: única fonte de verdade dos eventos globais.
- `assets`: identidade do ativo ao qual o evento pertence.
- `transactions`: histórico usado para reconstruir a posição elegível.
- `dividends`: legado reconstruível durante a transição; não é fonte canônica.
- Uma projeção por carteira somente poderá existir futuramente se medições
  demonstrarem necessidade. Nesse caso, deverá ser explicitamente derivada,
  versionada, invalidável e reconstruível.

## Fluxo alvo

1. Provedores publicam observações vinculadas ao ativo.
2. A reconciliação produz um evento econômico global em `asset_dividends`.
3. Endpoints e serviços de carteira consultam os eventos globais.
4. Um serviço canônico calcula a posição histórica na data de direito.
5. Proventos, Resumo, Patrimônio, Rentabilidade, snapshots e IRPF consomem o
   mesmo resultado derivado.

A carteira atual não define o histórico: um ativo já vendido pode continuar
gerando um direito histórico quando havia posição elegível. De modo equivalente,
possuir o ativo hoje não cria direito retroativo.

## Invariantes

- A identidade econômica não contém `portfolio_id`.
- A coleta não lê carteiras ou transações e não materializa direitos.
- Nenhum endpoint de carteira chama provedor externo.
- O mesmo evento global nunca é duplicado por carteira.
- Alterar uma transação histórica pode alterar o direito derivado, mas não o
  evento global.
- Eventos não monetários permanecem classificados no catálogo e não entram
  automaticamente em agregados de caixa.
- Ausência de posição elegível produz zero direito, não ausência do evento.
- Todos os consumidores financeiros usam uma única política para Data Com,
  Data Ex, pagamento, quantidade elegível, bruto, imposto e líquido.

## Migração incremental

### Bloco 1 — contrato e suspensão

- Formalizar este desenho.
- Marcar contrato e runbook v1 como suspensos.
- Proibir nova execução operacional.

### Bloco 2 — inventário de consumidores e portas de escrita

- Enumerar todas as leituras e escritas em `dividends`.
- Classificar cada consumidor por Proventos, Resumo, Patrimônio,
  Rentabilidade, snapshots, IRPF e APIs.
- Desativar rotas e integrações legadas incompatíveis sem remover dados.
- `POST /api/v1/sync/proventos/{portfolio_id}` e a integração
  `brapi_dividends.py` foram removidos por violarem a separação entre coleta
  global e consulta de carteira.

### Bloco 3 — serviço canônico de direitos

- Implementar cálculo derivado por evento e posição histórica.
- Definir política temporal auditável para Data Com/Data Ex.
- Centralizar bruto, imposto, líquido, moeda e tipos monetários.
- Cobrir carteira sem posição, compra na Data Ex, venda posterior e recompra.

### Bloco 4 — migração de consumidores

- Migrar um consumidor por commit pequeno.
- Comparar resultados legados e canônicos com fixtures e PostgreSQL.
- Não alterar o schema destrutivamente.

### Bloco 5 — contração do legado

- Confirmar zero consumidores e zero portas de escrita.
- Preservar/exportar evidência necessária.
- Remover `dividends` somente por migration separada e reversível.
- Atualizar contratos, documentação e Issues relacionadas.

### Bloco 6 — novo seed isolado

- Publicar novo contrato com escrita exclusiva em `asset_dividends`.
- Adquirir advisory lock antes de inspeção e rede.
- Separar gates de host, identidade da imagem e testes internos do container.
- Executar dry-run read-only antes de nova autorização.
- Provar duas execuções idempotentes somente após todos os gates.

## Critério de conclusão

A migração estará concluída quando:

- `asset_dividends` for a única fonte persistida dos eventos;
- nenhuma porta ativa gravar direitos por carteira;
- todos os consumidores usarem o cálculo derivado canônico;
- resultados financeiros tiverem paridade explicada e testada;
- `dividends` puder ser removida sem perda de informação canônica;
- um novo contrato operacional substituir formalmente a versão v1 suspensa.

Até lá, nenhuma execução do wrapper
`Invoke-PreProdDividendsIdempotency.ps1` está autorizada.
