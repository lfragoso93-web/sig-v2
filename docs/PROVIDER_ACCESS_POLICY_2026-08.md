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
