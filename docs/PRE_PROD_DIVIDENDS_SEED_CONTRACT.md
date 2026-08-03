# Contrato do seed isolado de proventos — `pre-prod-dividends-seed.v2`

> Issue dedicada: #226  
> Issue-mãe: #158  
> Gate agregado: #216  
> Estado: **CANÔNICO — execução condicionada à autorização operacional da Issue #226**
> Última atualização: 30/07/2026

## Objetivo

Reconstruir e validar exclusivamente o catálogo global de eventos em
`asset_dividends`. Direitos financeiros por carteira são projetados sob demanda
a partir das transações e não pertencem ao seed.

Este contrato não autoriza uma execução por si só. Cada janela operacional
exige branch, SHA, período, ambiente e aprovação explícita registrados na
Issue #226.

## Identidade e janela

- branch obrigatória: `stable-15jun`;
- `commit_sha`: SHA Git completo, hexadecimal minúsculo;
- `run_id`: `YYYYMMDD-HHMMSS`;
- datas inicial e final inclusivas, com início não posterior ao fim.

## Fronteira de dados

### Leitura

| Tabela | Uso |
|---|---|
| `assets` | identidade, classe e elegibilidade dos ativos |
| `asset_dividends` | baseline, cobertura e integridade do catálogo |

### Escrita

| Tabela | Operação |
|---|---|
| `asset_dividends` | criar ou atualizar eventos globais normalizados |

Nenhuma outra tabela é autorizada para leitura, inspeção ou escrita pelo
contrato v2.

## Garantias operacionais

- uma única sessão e uma única transação controlada pelo orquestrador;
- advisory transaction lock dedicado antes da persistência;
- nenhuma concorrência interna;
- provedores explícitos, sem converter falhas em resposta vazia;
- nenhum `commit` ou `rollback` nos serviços internos;
- rollback integral diante de erro ou achado canônico bloqueante;
- evidência vinculada ao `run_id`, branch e SHA executados;
- segunda execução controlada e comparação offline obrigatórias.

## Coleta e persistência

- BRAPI é a fonte principal e Yahoo histórico é complementar;
- valores históricos do Yahoo são revertidos à escala da Data Ex somente por
  fatores positivos de split/grupamento publicados após o evento; valor do
  provedor e fator acumulado permanecem no payload normalizado;
- respostas vazias exigem classificação explícita;
- somente eventos dentro da janela são persistidos;
- a identidade econômica usa ativo, Data Ex, tipo e pagamento efetivo;
- divergências entre fontes na mesma identidade são bloqueantes;
- eventos monetários e não monetários permanecem no catálogo global;
- o estágio nunca consulta posição, carteira ou direitos materializados.

## Envelope mínimo

```json
{
  "schema_version": "pre-prod-dividends-seed.v2",
  "generated_at": "ISO-8601 UTC",
  "run_id": "YYYYMMDD-HHMMSS",
  "identity": {
    "branch": "stable-15jun",
    "commit_sha": "sha completo"
  },
  "window": {},
  "sources": [],
  "authorized_tables": {
    "read": ["assets", "asset_dividends"],
    "write": ["asset_dividends"]
  },
  "before": {},
  "collection": {},
  "global_persistence": {},
  "after": {},
  "coverage": {},
  "groupings": [],
  "integrity": {},
  "transaction": {},
  "errors": [],
  "ok": true
}
```

Não existe seção `materialization`. Evidências v1 são rejeitadas explicitamente
pelo carregador v2.

## Métricas e integridade

O relatório contém:

- contagens de `assets` e `asset_dividends`;
- cobertura temporal mínima e máxima;
- ativos com eventos;
- agrupamentos por classe, tipo, fonte, ano e ticker;
- eventos globais duplicados;
- eventos órfãos de ativo;
- Data Ex ausente;
- valores monetários globais negativos.

Todos os achados de integridade v2 são bloqueantes. Métricas de `dividends`,
portfólios, elegibilidade ou materialização não fazem parte do envelope.

## Idempotência

Duas execuções consecutivas devem possuir:

- mesmo contrato, branch, SHA, janela e fronteira;
- baseline da segunda igual ao estado final da primeira;
- estado final, cobertura, agrupamentos, fontes e coleta estáveis;
- zero criações e atualizações físicas na segunda execução;
- zero achados de integridade.

O comparador offline mantém seu próprio schema
`pre-prod-dividends-seed-idempotency.v1`, mas aceita somente evidências do seed
`pre-prod-dividends-seed.v2`.

## Critérios de aborto

- identidade ou janela inválida;
- advisory lock indisponível;
- falha de transporte, autenticação, HTTP, parsing ou provedor;
- ativo coletado ausente do catálogo;
- conflito econômico entre fontes;
- tentativa de acesso fora da fronteira v2;
- duplicidade, referência órfã, Data Ex ausente ou valor negativo;
- falha ao publicar a evidência de forma atômica.

## Fora do escopo

- `dividends`, carteiras, transações e materialização de direitos;
- conversão cambial;
- posições, snapshots, rentabilidade, metas e IRPF;
- frontend e APIs;
- migrations destrutivas ou limpeza física de tabelas legadas.
