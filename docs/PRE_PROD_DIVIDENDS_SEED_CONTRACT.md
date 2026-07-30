# Contrato do seed isolado de proventos — `pre-prod-dividends-seed.v1`

> Issue dedicada: #226  
> Issue-mãe: #158  
> Gate agregado: #216  
> Estado: **SUSPENSO — contrato v1 incompatível com a arquitetura canônica aprovada**
> Última atualização: 30/07/2026

## Decisão arquitetural superveniente

A partir de 30/07/2026, este contrato v1 permanece somente como registro da
implementação existente e **não pode ser usado para autorizar execução**.

A arquitetura aprovada determina que:

- todo evento de provento pertence exclusivamente a um ativo;
- `asset_dividends` é a única fonte canônica global;
- carteira, posição e transação não participam da coleta nem da identidade do evento;
- o direito financeiro de uma carteira é calculado a partir do evento global e da
  posição histórica na data de direito;
- `dividends` é legado reconstruível, não uma segunda fonte de verdade;
- nenhuma coleta futura pode materializar direitos por carteira;
- a remoção física de `dividends` depende de inventário, migração de consumidores
  e prova de paridade.

As seções v1 abaixo descrevem o estado implementado antes dessa decisão. Qualquer
regra de leitura, escrita, materialização, métrica ou idempotência envolvendo
`dividends`, `portfolios` ou `transactions` está suspensa e será substituída
por um novo contrato após a migração descrita em
`docs/DIVIDENDS_CANONICAL_ARCHITECTURE.md`.

## Objetivo

Definir a fronteira operacional, o envelope de evidência e os critérios de segurança
do estágio isolado que reconstrói eventos globais de proventos e direitos
materializados por carteira após a limpeza controlada de pré-produção.

Esta especificação não autoriza escrita real. A execução somente poderá ocorrer
depois da implementação, revisão, testes, sincronização da documentação viva e
aprovação explícita da janela operacional.

## Princípios

- uma única entrada oficial para o estágio;
- uma única transação de trabalho;
- advisory lock PostgreSQL dedicado;
- nenhuma concorrência interna;
- nenhum `commit` em serviços chamados pela entrada;
- falhas de provedor não podem ser convertidas em “sem eventos”;
- rollback integral diante de erro, divergência ou escrita não autorizada;
- evidência vinculada ao `run_id`, branch e SHA executados;
- coleta global e materialização por carteira possuem métricas independentes;
- segunda execução controlada e comparador offline são obrigatórios.

## Fronteira de dados

### Tabelas autorizadas para leitura

| Tabela | Uso |
|---|---|
| `assets` | catálogo, identidade, classe e elegibilidade |
| `transactions` | posição na data de corte |
| `portfolios` | carteiras elegíveis para materialização |
| `asset_dividends` | baseline e UPSERT dos eventos globais |
| `dividends` | baseline e reconciliação dos direitos materializados |

### Tabelas autorizadas para escrita

| Tabela | Operação |
|---|---|
| `asset_dividends` | criar ou atualizar eventos globais normalizados |
| `dividends` | criar ou atualizar direitos materializados e rastreáveis |

### Somente inspeção

`dividends_sync_jobs` pode ser lida exclusivamente para inventário e decisão
posterior de contração. O estágio não deve criar, atualizar ou depender de jobs
nessa tabela.

### Escritas proibidas

O estágio não pode alterar:

- `asset_prices`;
- `rate_history`;
- `fx_rates`;
- `corporate_events`;
- `fixed_income_investments`;
- `portfolio_positions`;
- `portfolio_snapshots`;
- `portfolio_class_snapshots`;
- `transactions`;
- catálogo ou aliases B3/Tesouro;
- qualquer tabela não declarada na lista de escrita autorizada.

## Isolamento obrigatório

A entrada não pode disparar:

- B3/COTAHIST;
- Tesouro Direto;
- benchmarks macroeconômicos;
- câmbio;
- importação CSV;
- rebuild de posições;
- snapshots;
- scheduler diário;
- endpoint de sincronização em background;
- backfill pós-transação;
- asset seed;
- pipeline de mercado;
- `full_market_rebuild`.

## Fontes e cobertura

A evidência deve declarar, sem inferência implícita:

- fonte principal;
- fonte complementar, quando habilitada;
- janela temporal solicitada e efetiva;
- classes de ativo elegíveis;
- tickers escaneados, elegíveis, ignorados e sem cobertura;
- tipos de evento aceitos;
- quantidade de respostas válidas, vazias e com erro;
- cooldown, indisponibilidade ou limitação por provedor;
- payloads rejeitados e motivo.

BRAPI e Yahoo Finance não podem ser fundidos em uma lista sem preservar a origem
de cada evento. Indisponibilidade, rate limit, erro de parsing e resposta vazia
são estados distintos.

## Identidade operacional

A CLI deverá exigir:

- `--run-id` no formato `YYYYMMDD-HHMMSS`;
- `PRE_PROD_BRANCH=stable-15jun`;
- `PRE_PROD_COMMIT_SHA` com SHA completo;
- banco PostgreSQL compatível com o perfil autorizado;
- diretório de artefatos ainda inexistente;
- confirmação de que não existem processos concorrentes de proventos.

O relatório deve repetir a identidade efetivamente validada, sem aceitar valores
somente declarativos.

## Lock e transação

- usar advisory lock exclusivo do domínio de proventos;
- obter o lock antes de qualquer consulta externa que possa anteceder escrita;
- retornar exit code específico quando o lock já estiver ocupado;
- executar persistência global e materialização na mesma transação;
- impedir `commit`, `rollback` ou abertura de sessão autônoma nos serviços internos;
- executar rollback integral em exceção, erro bloqueante ou reconciliação inválida;
- liberar o lock em todos os caminhos de saída.

## Envelope mínimo

O JSON final deve conter, no mínimo:

```json
{
  "schema_version": "pre-prod-dividends-seed.v1",
  "generated_at": "ISO-8601 UTC",
  "run_id": "YYYYMMDD-HHMMSS",
  "identity": {
    "branch": "stable-15jun",
    "commit_sha": "SHA completo"
  },
  "window": {
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD"
  },
  "sources": [],
  "authorized_tables": {
    "read": [],
    "write": []
  },
  "before": {},
  "collection": {},
  "global_persistence": {},
  "materialization": {},
  "after": {},
  "coverage": {},
  "integrity": {},
  "transaction": {
    "final_state": "committed|rolled_back|blocked",
    "committed": false,
    "rollback_performed": false
  },
  "errors": [],
  "ok": false
}
```

Campos podem ser adicionados, mas os campos mínimos não podem ser removidos ou
ter semântica alterada dentro da versão `v1`.

## Métricas obrigatórias

### Baseline e estado final

- linhas em `asset_dividends`;
- linhas em `dividends`;
- cobertura temporal mínima e máxima;
- contagem por classe, tipo de evento, fonte, ano e ticker.

### Coleta

- ativos escaneados;
- elegíveis;
- ignorados por regra;
- sem cobertura;
- respostas válidas;
- respostas vazias;
- falhas por provedor;
- eventos recebidos e rejeitados.

### Persistência global

- eventos normalizados;
- criados;
- atualizados;
- inalterados;
- deduplicados;
- datas derivadas;
- moedas ausentes ou não suportadas.

### Materialização

- carteiras escaneadas;
- posições elegíveis;
- direitos criados;
- atualizados;
- inalterados;
- removidos ou cancelados, quando a regra futura autorizar;
- eventos não monetários excluídos das somas.

## Integridade

O relatório deve validar:

- zero referências órfãs entre `dividends` e `asset_dividends`;
- zero referências órfãs para ativo e carteira;
- duplicidades pela identidade econômica global persistida: ativo, Data Ex,
  tipo e pagamento efetivo, usando a Data Ex somente quando o pagamento for
  desconhecido;
- duplicidades por `portfolio_id + asset_dividend_id`;
- eventos com Data Ex ausente;
- Data Com ou pagamento ausentes;
- datas derivadas e regra aplicada;
- valores negativos ou incompatíveis com o tipo;
- JCP com regra líquida consistente;
- eventos não monetários fora dos agregados financeiros;
- nenhuma escrita detectada fora das tabelas autorizadas.

A unicidade global deve permitir eventos legítimos do mesmo ativo, Data Ex e
tipo quando o pagamento efetivo for distinto. Divergências de valor dentro da
mesma identidade continuam bloqueantes. A materialização permanece única por
`portfolio_id + asset_dividend_id`.

Quando uma mesma fonte publicar, na mesma Data Ex e tipo, um único total canônico
e duas ou mais parcelas explicitamente marcadas com pagamento estimado, as
parcelas somente podem ser absorvidas se a soma for equivalente ao total na
precisão canônica. A data provisória de pagamento das parcelas não participa
dessa comparação; o total preserva sua data efetiva. Soma divergente, ausência da
marca, total ambíguo ou parcela isolada continuam bloqueantes.

Uma fonte complementar que declare explicitamente semântica agregada por Data Ex
não compete com uma identidade individual quando a fonte principal publicar dois
ou mais componentes de tipos distintos nessa data. Os componentes tipados da
fonte principal permanecem canônicos e separados. Sem declaração explícita, com
apenas um tipo ou com Data Ex distinta, a divergência permanece bloqueante.

## Moeda e câmbio

A moeda do evento deve ser declarada quando o provedor a informar. Ausência de
moeda deve aparecer na evidência. Conversão cambial não pertence a este estágio
e não pode ser executada implicitamente.

## Política de erro

São bloqueantes:

- falha ou indisponibilidade de fonte obrigatória;
- payload obrigatório vazio sem classificação explícita;
- identidade operacional divergente;
- lock não adquirido;
- tentativa de escrita fora da fronteira;
- duplicidade ou referência órfã não explicada;
- erro de materialização;
- divergência entre contagens transacionais e pós-contagens;
- falha ao publicar a evidência de forma atômica.

Erros bloqueantes exigem `ok=false`, transação não confirmada e exit code
diferente de zero.

## Evidência e publicação

A evidência deve ser escrita em:

```text
artifacts/pre-prod-rebuild/<run-id>/dividends-seed.json
```

A publicação deve ser atômica, sem sobrescrever execução anterior. Artefatos não
devem ser versionados no Git nem conter URL de banco, credenciais, tokens ou
payloads sensíveis integrais.

## Idempotência

A prova exige duas execuções controladas com a mesma janela e sem mudança
conhecida das fontes. O comparador offline deve confirmar:

- mesma identidade de contrato;
- segunda execução com zero novas linhas físicas;
- mesmas contagens finais;
- mesma cobertura temporal;
- mesmos agrupamentos por classe, tipo, fonte, ano e ticker;
- zero duplicidades;
- zero órfãos;
- estado final estável;
- `ok=true` nas duas evidências e no comparador.

Se a fonte mudar entre execuções, a diferença deve ser explicada e uma nova dupla
controlada deve ser produzida.

## Gates antes da execução real

- [x] implementação dividida em commits pequenos;
- [x] coletor estrito sem commit e sem fallback silencioso;
- [x] persistência global transacional;
- [x] materialização transacional;
- [x] advisory lock;
- [x] inspeções de integridade e cobertura;
- [x] CLI e exit codes;
- [x] comparador offline;
- [x] wrapper PowerShell;
- [x] testes unitários e de integração;
- [x] suíte backend completa no SHA operacional;
- [x] README, ROADMAP, CHANGELOG e runbook sincronizados;
- [ ] Issues #158, #216 e #226 reconciliadas com evidências reais;
- [ ] revisão explícita da janela real.

## Fora de escopo

- remoção física imediata de campos legados;
- conversão cambial;
- evolução completa de provedores internacionais;
- alterações de Resumo, Patrimônio, Rentabilidade ou frontend de Proventos;
- importação, posições, snapshots e reconciliação financeira final.
