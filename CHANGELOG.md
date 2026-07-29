# Changelog — SGI v2

Todas as mudanças relevantes do projeto são documentadas aqui.
Formato baseado em Keep a Changelog.

## [Unreleased] — branch `stable-15jun`

### Corrigido — reconciliação de parcelas estimadas de proventos (29/07/2026)

- Eventos de uma mesma fonte, identidade e pagamento passaram a reconhecer um total canônico acompanhado por duas ou mais parcelas marcadas como pagamento estimado somente quando a soma é equivalente na precisão canônica.
- Divergência de soma, ausência da marca, total ambíguo ou parcela isolada permanecem bloqueantes.
- Adicionada regressão para o payload real da ABEV3 em 2015, sem exceção por ticker e sem alterar a identidade econômica persistida.

### Corrigido — compatibilidade do identificador Alembic de proventos (29/07/2026)

- O identificador da migration de identidade econômica foi reduzido para `20260729_dividend_identity`, respeitando o limite `VARCHAR(32)` de `alembic_version.version_num`.
- A validação estrutural de revisions agora reconhece atribuições Python anotadas (`revision: str = ...`), impedindo que novos identificadores longos escapem do gate.
- A tentativa operacional no SHA `60e30b5818d1ef91c0308b800ee29a978010d8f6` falhou antes do seed e sofreu rollback integral; a idempotência permanece pendente e exige nova autorização vinculada ao SHA corrigido.

### Corrigido — identidade econômica de eventos globais de proventos (29/07/2026)

- A identidade persistida deixou de colapsar eventos legítimos do mesmo ativo, Data Ex e tipo quando possuem datas efetivas de pagamento distintas.
- A persistência estrita agora aceita eventos divergentes da mesma fonte somente quando a identidade econômica persistida também é distinta; divergências na mesma identidade e conflitos entre fontes continuam bloqueantes.
- A migration substitui a constraint antiga por índice único sobre ativo, Data Ex, tipo e `COALESCE(payment_date, ex_date)`, preservando idempotência para pagamentos ausentes.
- Tickers fracionários, direitos e recibos passaram a usar uma política compartilhada de inelegibilidade antes de qualquer consulta às fontes principal e complementar, evitando símbolos inválidos como `ONCO11F.SA`.
- Regressões cobrem os dois JCPs reais de ABEV3 em `2025-12-19`, a migration, a filtragem de `ONCO11F` e os conflitos materiais já protegidos.

### Corrigido — semântica da fonte complementar e precisão multifuente de proventos (29/07/2026)

- Datas do histórico da fonte complementar agora são normalizadas como Data Ex, sem serem apresentadas incorretamente como data efetiva de pagamento.
- A fonte principal permanece canônica e determinística independentemente da ordem de entrada, preservando sua data de pagamento, valor e proveniência.
- Valores monetários da fonte complementar truncados entre seis e oito casas são equivalentes somente quando a escala é declarada no payload normalizado e corresponde à projeção truncada do valor da fonte principal; divergências materiais e eventos com identidades distintas continuam bloqueantes.
- Regressões cobrem o evento real de AALR3, ordem invertida das fontes, proveniência, datas Ex/pagamento distintas, precisão permitida, conflito material e rollback transacional.

### Corrigido — evidência de conflitos multifuente de proventos (28/07/2026)

- Diagnósticos bloqueantes agora registram, por campo, os valores normalizados de cada fonte sem expor payload bruto.
- A política de equivalência, a tolerância numérica, a identidade global e o rollback integral permanecem inalterados.
- Regressões exigem a renderização determinística de datas e valores divergentes; a execução real da Issue #226 continua pendente.

### Corrigido — reconciliação multifuente de proventos (28/07/2026)

- A persistência passou a comparar somente atributos econômicos canônicos presentes em ambas as fontes, sem tratar proveniência e payload bruto distintos como conflito.
- Diferenças numéricas de até oito casas decimais são aceitas de acordo com a precisão persistida; divergências materiais de valor, datas ou metadados comuns continuam bloqueantes.
- Mensagens de conflito agora identificam os campos divergentes, preservando evidência auditável sem escolher silenciosamente uma fonte.
- Adicionadas regressões para eventos equivalentes, tolerância numérica, conflito real de data/valor e identidades globais distintas; a execução real da Issue #226 permanece pendente.

### Corrigido — classificação de cobertura complementar em proventos (28/07/2026)

- Símbolos ausentes na fonte complementar passaram a ser registrados como `provider_no_coverage_ticker_missing`, sem converter falta de cobertura em indisponibilidade global do provedor.
- Timeouts, erros HTTP e demais falhas operacionais permanecem bloqueantes, preservando o contrato sem fallback silencioso.
- O aviso de compatibilidade `Timestamp.utcnow` da integração passou a ser filtrado somente dentro da consulta de histórico, sem ocultar outras advertências.
- Adicionadas regressões para BDR sem cobertura, timeout e erro HTTP; as duas execuções reais da Issue #226 permanecem pendentes.

### Corrigido — esquema do controle de sincronização de proventos (28/07/2026)

- Adicionada migration Alembic para materializar `dividends_sync_jobs`, tabela técnica já declarada pelo ORM e classificada como reconstruível no inventário.
- Corrigida a falha operacional `SQLSTATE 42P01` encontrada na inspeção inicial do seed isolado de proventos.
- Adicionada regressão que confere todas as colunas do modelo, o índice único de `job_name`, o encadeamento no head Alembic e o downgrade.
- A tentativa no SHA `6a3560f532857d8938727157a23e56d78670cca5` foi abortada antes da coleta e da persistência; as duas execuções reais da Issue #226 permanecem pendentes e exigem nova autorização vinculada ao novo SHA.

### Corrigido — gate de validação do seed de proventos (28/07/2026)

- Removidas 82 linhas de teste Python anexadas indevidamente ao wrapper `Invoke-PreProdDividendsIdempotency.ps1`, sem alterar sua lógica operacional.
- Restaurada a neutralidade de provedores no README público.
- Suíte específica aprovada em 121/121 testes e suíte backend integral aprovada em 982/982 testes no novo SHA operacional.
- README, ROADMAP, contrato e Issue #226 sincronizados; duas execuções reais controladas permanecem pendentes e não autorizadas.

### Adicionado — runbook operacional do seed isolado de proventos (28/07/2026)

- Criado `docs/pre-prod-dividends-seed-runbook.md` com pré-requisitos, fronteira autorizada, validação, comando PowerShell oficial, códigos de saída e critérios de sucesso e aborto.
- Documentada a dupla execução pelo wrapper `Invoke-PreProdDividendsIdempotency.ps1` e a preservação atômica de `first.json`, `second.json` e `idempotency.json`.
- README, ROADMAP e contrato `pre-prod-dividends-seed.v1` foram sincronizados com a implementação real de coleta estrita, persistência, materialização, inspeções, CLI e comparador.
- A publicação do runbook não autoriza execução real; suíte integral no SHA operacional, janela aprovada e duas execuções controladas continuam pendentes na Issue #226.
- Nenhuma coleta, escrita em banco, migration ou execução em pré-produção ocorreu neste bloco documental.

### Adicionado — contrato do seed isolado de proventos (28/07/2026)

- Criada a Issue #226 e vinculada às Issues #158 e #216 como gate dedicado do estágio.
- Publicado `docs/PRE_PROD_DIVIDENDS_SEED_CONTRACT.md` com o contrato `pre-prod-dividends-seed.v1`.
- Limitadas as leituras a `assets`, `transactions`, `portfolios`, `asset_dividends` e `dividends` e as escritas a `asset_dividends` e `dividends`.
- Definidos advisory lock dedicado, transação única, rollback integral, identidade por `run_id`/branch/SHA, métricas de cobertura e integridade e prova offline de idempotência.
- Scheduler, endpoints em background, B3, Tesouro, benchmarks, câmbio, importação, posições, snapshots e `full_market_rebuild` permanecem fora do estágio.
- README, ROADMAP, runbook geral e auditoria arquitetural foram sincronizados; nenhuma CLI, migration ou escrita em pré-produção foi executada.
- A PR #221 permanece não aplicada por incompatibilidade entre TypeScript 7 e `typescript-eslint`.

### Corrigido — compatibilidade da consulta PTAX oficial (28/07/2026)

- Removida a opção OData `$orderby=dataHoraCotacao asc`, rejeitada com HTTP 400 pelo endpoint oficial `CotacaoDolarPeriodo`.
- Mantidos `$select=cotacaoVenda,dataHoraCotacao`, deduplicação diária, ordenação local e seleção do boletim mais recente no parser estrito.
- Adicionada regressão unitária exigindo que `$orderby` não seja enviado.
- A consulta read-only retornou cinco PTAX de venda entre `2026-07-20` e `2026-07-24`.
- As execuções `20260728-103750` e `20260728-104238`, no commit `37c1d800be6f21dfc5c91b332a6ebe8748c0ac1c`, comprovaram idempotência com estado final estável em 6 linhas, zero crescimento na segunda execução, zero duplicidades, zero pares não suportados e `ok=true`.
- A Issue #217 foi encerrada após a reconciliação operacional.

### Adicionado — seed isolado de câmbio e runbook operacional (27/07/2026)

- Criado o contrato `pre-prod-fx-seed.v1` para o par `USD-BRL`, fonte oficial `BCB` e tipo `PTAX_SELL`.
- Implementadas inspeção read-only, cliente PTAX estrito sem fallback, preparação com persistência `commit=False`, advisory lock dedicado, transação única, commit final e rollback integral.
- Criada a CLI `python -m app.cli.pre_prod_fx_seed` com identidade obrigatória, intervalo inicial/final, sessões separadas para lock e trabalho, saída JSON e códigos de saída distintos.
- Respostas vazias, datas duplicadas, linhas fora da janela, pares não suportados e inconsistências finais são bloqueantes.
- Criado `docs/pre-prod-fx-seed-runbook.md` com validação unitária, comando PowerShell para duas execuções consecutivas, critérios de sucesso, aborto e evidências exigidas.
- README e ROADMAP foram sincronizados para marcar a estrutura do estágio como concluída e a execução real/idempotência como pendentes na Issue #217.
- A suíte incremental do estágio foi validada localmente com 37 testes aprovados antes do bloco documental.
- Nenhuma coleta PTAX ou escrita em pré-produção foi executada durante a implementação e documentação.

### Adicionado — persistência e fechamento operacional do seed macro (25/07/2026)

- Criado `scripts/compare_pre_prod_macro_seed.ps1` para persistir a prova offline em `macro-seed-compare.json`.
- O wrapper recusa sobrescrita, valida `pre-prod-macro-seed-compare.v1`, exige `ok=true` e propaga falha operacional.
- Adicionado teste estrutural do wrapper, com skip explícito quando o checkout backend não inclui `scripts/`.
- Criado `docs/pre-prod-macro-seed-runbook.md` com escopo, comandos, critérios de aborto e fronteira arquitetural.
- README e ROADMAP foram sincronizados com a execução real dos runs `20260725-231557` e `20260725-231604`.
- A comparação comprovou mesmo commit, estado final estável, zero novas linhas, zero duplicidades, zero indicadores não suportados e `ok=true`.
- Câmbio e proventos permanecem fora do estágio de benchmarks e devem usar contratos, locks, transações e evidências independentes.

### Corrigido — semântica da idempotência do seed macro (25/07/2026)

- O comparador deixou de tratar `imported` como quantidade de linhas novas, pois o serviço conta linhas submetidas ao UPSERT, incluindo conflitos atualizados.
- Novas linhas da segunda execução passaram a ser medidas pelo delta real entre `before.total_rows` e `after.total_rows`.
- A validação preserva o volume processado em `imported` sem produzir falso negativo quando o estado persistido permanece estável.
- Testes cobrem UPSERT sem crescimento e crescimento real da tabela.

### Corrigido — encoding das evidências macro no Windows (25/07/2026)

- O comparador offline passou a ler JSON com `utf-8-sig`, aceitando evidências UTF-8 com ou sem BOM.
- Erros de decodificação são normalizados como violações do contrato operacional.
- Adicionada regressão específica para arquivos produzidos pelo Windows PowerShell.

### Adicionado — seed isolado de benchmarks macroeconômicos (25/07/2026)

- Criado o contrato `pre-prod-macro-seed.v1` para CDI, SELIC, IPCA e IGPM.
- Implementados inspeção read-only, advisory lock dedicado, transação única, commit final e rollback integral.
- `benchmark_rate_service` passou a aceitar sessão externa e `commit=False` sem alterar consumidores existentes.
- Criada a CLI `python -m app.cli.pre_prod_macro_seed` com identidade obrigatória, saída JSON e exit codes distintos.
- Criado `scripts/pre_prod_macro_seed.ps1` para executar o estágio no container e preservar `macro-seed.json` por `run_id`.
- Criado o comparador puro `pre-prod-macro-seed-compare.v1` para provar idempotência sem acessar banco ou rede.
- A suíte do estágio cobre contrato, inspeção, serviço, CLI, wrapper e comparação offline.

### Corrigido — portabilidade do teste do wrapper de idempotência (25/07/2026)

- O teste estrutural deixou de assumir um layout físico único para o checkout, que divergia entre GitHub Actions (`<repo>/backend/tests/...`) e a imagem Docker (`/app/tests/...`).
- O wrapper agora é localizado por descoberta de ancestrais até `scripts/Invoke-PreProdTreasuryIdempotency.ps1`, preservando a validação completa no checkout do repositório.
- Quando o artefato em teste não inclui `scripts/` — como ocorre na imagem backend construída com contexto `backend/` — a suíte faz `skip` explícito em vez de produzir falso negativo.
- O comando operacional desse teste deve ser executado no checkout completo/CI; dentro do container Docker ele valida apenas que o artefato não inclui o wrapper por desenho.
- Nenhum seed, comparador ou escrita em pré-produção foi executado neste bloco.

### Corrigido — encoding das evidências de idempotência do Tesouro (25/07/2026)

- O wrapper deixou de usar `Tee-Object -FilePath`, cujo encoding implícito no Windows PowerShell produziu evidências UTF-16 incompatíveis com o contrato JSON UTF-8.
- `first.json`, `second.json` e `idempotency.json` agora são persistidos explicitamente como UTF-8 sem BOM por `System.IO.File.WriteAllText`.
- O exit code nativo de cada comando Docker é capturado antes da renderização e persistência da saída.
- Testes estruturais cobrem o encoding explícito, a ausência de `Tee-Object -FilePath` e a preservação dos exit codes.
- O incidente ocorreu somente no comparador offline: as duas execuções do seed retornaram `ok=true`, `required_empty_payloads=0`, integridade reconciliada e estado final estável em 88.638 preços.

### Corrigido — classificação de payloads vazios do Tesouro (25/07/2026)

- O histórico oficial passou a separar payloads vazios bloqueantes de ausências esperadas para títulos vencidos.
- `history.empty_payloads` foi preservado como total auditável, com os novos campos `required_empty_payloads`, `expected_empty_payloads`, `required_empty_symbols` e `expected_empty_symbols`.
- Símbolos com vencimento `DDMMAAAA` usam a data exata; séries com ano apenas são consideradas vencidas após `31/12` do ano publicado.
- Símbolos sem vencimento reconhecível permanecem bloqueantes por segurança.
- O orquestrador agora falha somente quando `required_empty_payloads` é diferente de zero, mantendo compatibilidade com evidências antigas que publicam apenas `empty_payloads`.
- Testes cobrem títulos vigentes, vencidos, símbolos sem vencimento, ausência esperada, ausência bloqueante e contrato legado.
- O runbook foi sincronizado com o incidente operacional, o rollback confirmado e os novos critérios de aborto e sucesso.

### Adicionado — wrapper operacional de idempotência do Tesouro (25/07/2026)

- Criado `scripts/Invoke-PreProdTreasuryIdempotency.ps1` como entrada oficial para duas execuções consecutivas do seed isolado do Tesouro.
- O wrapper exige branch `stable-15jun`, `HEAD` igual ao SHA informado e confirmação exata `EXECUTE-TREASURY-IDEMPOTENCY:<SHA40>` antes de qualquer Docker.
- São gerados dois `run_id` distintos e preservados `first.json`, `second.json` e `idempotency.json` em diretório operacional determinístico.
- `ArtifactRoot` passou a aceitar somente caminhos relativos dentro de `artifacts`, com separação explícita entre caminhos do host e `/app/artifacts/...` no container.
- O comparador canônico offline é executado após as duas evidências e seu exit code é propagado sem alteração.
- Testes estruturais cobrem confirmação, identidade Git, duas execuções, volume de artefatos e ausência de avaliação dinâmica.
- README, ROADMAP e o runbook do Tesouro foram sincronizados.
- Os CIs #664 e #666 foram aprovados; nenhum seed, banco ou fonte oficial foi acessado durante a implementação.

### Adicionado — prova offline de idempotência do seed do Tesouro (25/07/2026)

- Criado o contrato puro `pre-prod-treasury-seed-idempotency.v1` para comparar
  duas evidências consecutivas do seed isolado do Tesouro.
- A comparação exige `run_id` distintos, mesma branch, mesmo `commit_sha`,
  baseline encadeado, contagens finais estáveis e cobertura temporal estável.
- Adicionada a CLI offline
  `python -m app.cli.pre_prod_treasury_seed_idempotency` para ler dois arquivos
  JSON UTF-8 e publicar o relatório canônico sem acessar banco ou rede.
- Os códigos de saída distinguem idempotência comprovada (`0`), divergência
  estrutural (`1`) e entrada ou contrato inválido (`2`).
- Testes cobrem sucesso, identidade divergente, estado instável, execução com
  falha, JSON inválido e arquivo ausente.
- README, ROADMAP e o runbook do Tesouro foram sincronizados.
- Nenhum seed, coleta ou escrita foi executado na pré-produção.

### Adicionado — identidade operacional do seed do Tesouro (25/07/2026)

- O contrato `pre-prod-treasury-seed.v1` passou a registrar `run_id`, branch e
  `commit_sha` no JSON final.
- A CLI exige `run_id` no formato `YYYYMMDD-HHMMSS`, branch `stable-15jun` e
  SHA Git hexadecimal minúsculo com 40 caracteres.
- A identidade é validada antes da abertura de qualquer sessão de banco.
- Entrada inválida retorna código operacional `1`, sem traceback e sem acesso
  ao banco.
- Testes de contrato, serviço e CLI cobrem serialização, propagação e rejeição
  segura da identidade.
- README, ROADMAP e o runbook do Tesouro foram sincronizados.
- Nenhum seed, coleta ou escrita foi executado na pré-produção.

### Adicionado — seed transacional isolado do Tesouro Direto (25/07/2026)

- Criado o contrato `pre-prod-treasury-seed.v1` com baseline, pós-contagens,
  cobertura temporal e validações de integridade.
- Catálogo e histórico oficial do Tesouro passaram a compartilhar uma única
  sessão de trabalho e são executados com `commit=False`.
- O orquestrador confirma o estágio somente após a inspeção final reconciliada
  e executa rollback integral em erro, divergência ou exceção.
- Um advisory lock PostgreSQL dedicado impede execuções concorrentes.
- Criada a CLI `python -m app.cli.pre_prod_treasury_seed` com saída JSON e
  códigos distintos para sucesso, falha operacional, concorrência e falha inesperada.
- Adicionados testes unitários de contrato, inspeção, sessão, commit, rollback e CLI.
- Criado `docs/pre-prod-treasury-seed-runbook.md` e sincronizados README e ROADMAP.
- O CI da PR #209 passou; nenhuma execução, coleta ou escrita foi realizada na pré-produção.

### Corrigido — ajuda não destrutiva das CLIs do Tesouro (25/07/2026)

- As quatro CLIs operacionais do Tesouro passaram a validar argumentos com
  `argparse` antes de abrir sessão de banco ou iniciar qualquer serviço.
- `--help` agora imprime a interface e encerra com código `0`, sem sincronizar,
  reconstruir ou auditar dados.
- Argumentos desconhecidos deixam de ser silenciosamente ignorados.
- Adicionada regressão parametrizada cobrindo catálogo, rebuild oficial e as
  duas auditorias.

### Adicionado — estágio isolado B3 COTAHIST (24/07/2026)

- Criada a CLI `pre_prod_b3_seed` para executar somente catálogo nacional e
  histórico oficial COTAHIST, sem Tesouro, cripto, benchmarks, proventos ou snapshots.
- Período e data de corte são obrigatórios e aparecem no JSON final.
- O estágio registra contagens de ativos e preços antes/depois, resultados do
  catálogo e COTAHIST e retorna exit code diferente de zero diante de erros.
