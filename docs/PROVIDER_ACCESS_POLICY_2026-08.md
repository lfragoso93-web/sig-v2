# Política de acesso a provedores externos — SGI v2

Issue-mãe: #227  
Issue executora da auditoria: #247  
Bootstrap e fronteira operacional: #248

## Regra canônica

O SGI v2 é DB-first. Dados externos devem ser persistidos antes de participar de cálculos financeiros, relatórios ou projeções.

Existem somente três contextos autorizados para consulta externa:

1. **bootstrap completo do ambiente** antes da liberação para usuários/carteiras reais;
2. **preços recorrentes** durante o runtime normal:
   - preço intraday;
   - preço de fechamento diário;
3. **resolução pontual de lacuna histórica de preço**, quando uma data necessária não possuir cotação persistida suficiente no banco.

Qualquer outro acesso externo em request funcional ou job recorrente é violação arquitetural.

## Bootstrap completo

Antes de considerar o ambiente pronto para uso real, um bootstrap idempotente e certificável deve preencher e reconciliar, quando aplicável:

- catálogo de ativos e metadados;
- histórico de preços;
- Tesouro Direto e seu histórico;
- benchmarks/taxas;
- câmbio histórico necessário;
- Proventos globais;
- eventos corporativos;
- dados de roteamento/provider necessários aos adapters;
- demais séries externas exigidas pelos contratos financeiros estabilizados.

O processo HTTP pode estar tecnicamente vivo antes disso, mas o ambiente não deve ser declarado **ready para dados reais** até o bootstrap terminar e seus gates de cobertura passarem.

### Hierarquia de fontes — Tesouro Direto

Para o domínio `TESOURO_DIRETO`, a fonte primária de catálogo e histórico é o **Tesouro Transparente**, usando o conjunto oficial de taxas e preços dos títulos ofertados pelo Tesouro Direto.

Regras:

1. o catálogo canônico é derivado do histórico oficial, preservando títulos que já não estejam na oferta corrente;
2. a identidade usa a família do título e seu vencimento oficial, conforme normalização canônica do SGI;
3. a BRAPI é somente fallback operacional quando a fonte oficial não produzir catálogo utilizável;
4. entradas sintéticas não podem ser persistidas como `Asset` canônico;
5. resolução de ticker/nome durante requests e reconciliações usa somente o catálogo já persistido;
6. falha/ausência da fonte oficial deve ser observável; o fallback BRAPI não transforma uma cobertura parcial em certificação de completude histórica.

### Contrato de fontes — Criptomoedas

Para o domínio `CRIPTO`, a pertença ao catálogo retornado por `/api/v2/crypto/available` é a autoridade operacional de elegibilidade do bootstrap. O SGI não infere que um símbolo é inválido por nome, tamanho ou sufixo; símbolos como tokens agregados ou representações tokenizadas continuam pertencendo ao domínio quando a própria fonte canônica os lista como `coins`.

Regras:

1. a BRAPI é a fonte primária e o contrato persistido do ativo permanece em BRL;
2. respostas `range=max` com evidência de truncamento são marcadas `HISTORY_START_TRUNCATED`, sem fingir completude histórica;
3. quando a BRAPI retorna zero linhas para `missing_all`, o fallback autorizado é Yahoo no par `*-USD`, nunca `*-BRL`, com conversão obrigatória pela PTAX USD-BRL já persistida antes da escrita;
4. quando Yahoo USD/PTAX é a fonte efetiva de um histórico inicial completo, a metadata registra `provider=yfinance` e `provider_symbol=*-USD`, enquanto os preços persistidos continuam em BRL;
5. o complemento de um histórico BRAPI truncado também usa Yahoo em USD + PTAX, preservando BRAPI como provider primário do ativo;
6. preços Yahoo/PTAX usam proveniência explícita `yfinance_crypto_ptax_brl_max` e não sobrescrevem timestamps já persistidos;
7. complemento vazio ou indisponível de um início BRAPI truncado recebe `HISTORY_START_COMPLEMENT_UNAVAILABLE`: a lacuna continua observável, mas o bootstrap global não repete automaticamente a mesma consulta em todas as execuções;
8. complemento não vazio que não alcança a véspera da primeira data persistida pela BRAPI recebe `HISTORY_START_COMPLEMENT_GAPPED`: a costura histórica permanece explicitamente não certificada e também não entra em retry automático infinito;
9. `HISTORY_START_EXHAUSTED` só é usado quando existe evidência de complemento histórico utilizável e contínuo até a janela BRAPI, quando Yahoo USD/PTAX fornece histórico inicial utilizável após BRAPI vazio, ou quando a própria resposta inicial da BRAPI pode ser classificada como completa pelos gates do adapter;
10. `HISTORY_UNAVAILABLE` é terminal somente quando a tentativa inicial não produz nenhuma linha utilizável nem na BRAPI nem no Yahoo USD/PTAX; esse estado não entra em retry automático e permanece observável para auditoria;
11. resposta inicial BRAPI excessivamente rasa e recente (até 7 linhas, com início nos 30 dias anteriores ao `required_to`) recebe `HISTORY_START_SHALLOW`; esse estado é bloqueante para readiness, não entra em retry automático e exige probe/reconciliação deliberada antes de qualquer complemento;
12. shallow history existente só é elegível à recuperação quando uma probe Yahoo `max` comprova histórico anterior à primeira data BRAPI persistida (`recoverable_shallow`); recuperação é opt-in, limitada por lote, preserva a linha BRAPI existente e persiste somente Yahoo USD/PTAX anterior à janela BRAPI, mantendo `GAPPED`/`UNAVAILABLE` como findings bloqueantes quando a costura não puder ser certificada;
13. quando essa recuperação comprova costura contínua até a véspera da janela BRAPI, mas o histórico completo disponível continua naturalmente curto (até 7 linhas dentro da janela de 30 dias), o ativo recebe `HISTORY_START_SHALLOW_VERIFIED`; esse status registra shallow legítimo/verificado e não bloqueia readiness nem entra novamente na auditoria de shallow não reconciliado;
14. quando a probe Yahoo `max` não comprova qualquer histórico anterior à janela BRAPI já persistida, o ativo recebe `HISTORY_START_SHALLOW_UNAVAILABLE`: o estado sai da fila automática para evitar retry infinito, mas continua bloqueando readiness e não equivale a histórico verificado/completo;
15. probes de diagnóstico de provider são superfícies read-only e nunca persistem `Asset`, metadata de provider ou `asset_prices`.

## Runtime normal

Após o bootstrap:

### Permitido

- atualização de `Asset.last_price`/cache para preço intraday;
- persistência do fechamento diário em `asset_prices` e séries dedicadas de preço;
- invalidação de caches dependentes após atualização de preço;
- manutenção local de snapshots/TWR sobre dados já persistidos.

### Proibido como recorrência

- atualizar catálogo ou metadados;
- buscar logos;
- sincronizar Proventos ou eventos corporativos;
- importar benchmarks/taxas;
- executar seed ou rebuild amplo de domínio;
- executar onboarding de ativo por criação de transação;
- consultar provider em páginas, KPIs, relatórios, posição, IRPF, Proventos ou Rentabilidade.

Esses dados são atualizados pelo bootstrap executado na subida controlada do ambiente, não por requests ou jobs recorrentes de domínio.

## Exceção: lacuna de preço em data específica

Quando um cálculo exigir uma cotação histórica e a leitura DB-first não encontrar cobertura suficiente para a data de referência, é permitido um fallback externo **pontual**.

Regras obrigatórias:

1. consultar primeiro o banco;
2. confirmar a ausência de cobertura para a data necessária;
3. solicitar ao provider somente a janela mínima necessária para resolver aquela data;
4. validar ticker, tipo, data e preço retornado;
5. persistir o resultado em `asset_prices` (ou série dedicada equivalente) com fonte explícita;
6. refazer a leitura pelo contrato DB-first;
7. nunca retornar ao cálculo financeiro um valor externo que não tenha sido persistido;
8. não transformar a exceção em backfill amplo silencioso;
9. manter idempotência e constraint de unicidade;
10. se o provider não resolver a lacuna, preservar ausência/erro explícito em vez de inventar zero ou preço stale de outra data.

`get_price_at_date()` permanece leitor puro e nunca chama provider. A exceção está isolada em `price_date_gap_resolver_service.py`, que:

- só consulta provider depois de uma leitura DB-first retornar `None`;
- limita a janela a `target_date - 5 dias .. target_date`, igual à tolerância temporal do leitor canônico;
- não cria ativo ausente;
- não usa `period=max`, backfill global ou `stale_snapshot`;
- usa histórico dedicado do Tesouro para `TESOURO_DIRETO`;
- persiste em `asset_prices` antes de refazer `get_price_at_date()`.

O resolvedor deve ser chamado apenas por fluxos que realmente necessitem resolver uma lacuna histórica; ele não é um substituto global para o leitor DB-first.

## Scheduler

O scheduler recorrente deve conter somente:

- preço intraday;
- fechamento diário de preços;
- manutenção local que não chama provider, como snapshots/TWR.

Tesouro pode usar pipeline dedicado de **preço** no fechamento. Isso não autoriza atualização recorrente de catálogo ou outros metadados.

## Requests HTTP

Requests financeiros são DB-first.

Uma rota interativa de cotação intraday pode consultar provider porque preço intraday é uma exceção autorizada. Busca de catálogo/sugestão deve evoluir para o catálogo persistido do bootstrap; não deve depender de provider para funcionar no runtime normal.

## Gate para dados reais

Nenhuma carteira real deve ser criada/importada antes de existir evidência de:

- bootstrap concluído;
- cobertura mínima certificada dos domínios externos necessários;
- scheduler restrito à política acima;
- leitores financeiros DB-first;
- fallback por data limitado à exceção documentada;
- testes estruturais verdes.
