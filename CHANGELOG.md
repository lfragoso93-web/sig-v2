# Changelog — SGI v2

Todas as mudanças relevantes do projeto são documentadas aqui.
Formato baseado em Keep a Changelog.

## [Unreleased] — branch `stable-15jun`

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
