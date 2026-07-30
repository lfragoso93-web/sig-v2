# Runbook — seed isolado de proventos

> **EXECUÇÃO SUSPENSA**
>
> Este runbook descreve a implementação v1 e não autoriza o uso da CLI, do
> comparador ou do wrapper. A arquitetura aprovada em 30/07/2026 tornou
> `asset_dividends` a única fonte canônica e retirou a materialização por carteira
> do pipeline de coleta. Retome operações somente após a migração incremental, a
> publicação de um novo contrato e uma nova autorização explícita na Issue #226.
>
> Consulte `docs/DIVIDENDS_CANONICAL_ARCHITECTURE.md`.

## Objetivo

Executar exclusivamente a coleta global em `asset_dividends` e a materialização
por carteira em `dividends`, usando o contrato
`pre-prod-dividends-seed.v1`, uma única transação e prova offline de
idempotência.

Este estágio pertence à Issue #226 e não executa B3/COTAHIST, Tesouro Direto,
benchmarks, câmbio, importação CSV, posições, snapshots, schedulers,
endpoints em background ou `full_market_rebuild`.

## Estado operacional

A CLI, o comparador offline e o wrapper PowerShell v1 estão implementados, mas
estão **suspensos**. A presença dessas entradas no repositório não autoriza
execução em qualquer ambiente operacional.

Antes de cada operação, a Issue #226 deve registrar:

- SHA completo aprovado da `stable-15jun`;
- janela temporal inicial e final;
- ambiente e banco alvo, sem credenciais;
- confirmação de ausência de processos concorrentes de proventos;
- responsável e janela operacional;
- autorização explícita para as duas execuções consecutivas.

## Fronteira autorizada

Leitura:

- `assets`;
- `transactions`;
- `portfolios`;
- `asset_dividends`;
- `dividends`.

Escrita:

- `asset_dividends`;
- `dividends`.

`dividends_sync_jobs` permanece somente para inspeção. Qualquer escrita fora
das duas tabelas autorizadas ou disparo de outro estágio exige aborto.

## Garantias da entrada oficial

O fluxo executa, sequencialmente:

1. valida identidade e janela antes de abrir banco ou rede;
2. adquire o advisory lock transacional dedicado;
3. captura a inspeção inicial;
4. coleta BRAPI como fonte principal e Yahoo como fonte complementar;
5. filtra e normaliza os eventos dentro da janela;
6. persiste o catálogo global;
7. materializa direitos por carteira;
8. executa `flush` e a inspeção final;
9. confirma uma única transação somente quando a reconciliação é válida;
10. executa rollback integral diante de erro ou divergência;
11. publica a evidência do contrato sem expor credenciais.

Os serviços internos não executam `commit` ou `rollback`. Eventos não
monetários permanecem no catálogo global e não são materializados como direito
financeiro.

## Pré-requisitos

1. Checkout limpo da `stable-15jun`.
2. `HEAD` exatamente igual ao SHA aprovado na Issue #226.
3. Imagem do backend reconstruída a partir desse mesmo checkout.
4. Backend, PostgreSQL e Redis saudáveis.
5. Acesso aos provedores BRAPI e Yahoo validado sem registrar tokens.
6. Nenhum scheduler, endpoint, backfill ou pipeline de proventos concorrente.
7. Janela temporal curta e explicitamente aprovada.
8. Diretório de artefatos relativo e localizado sob `artifacts`.
9. Suíte específica e regressão integral aprovadas no mesmo SHA.

Validação inicial em PowerShell:

```powershell
git fetch origin
git switch stable-15jun
git pull --ff-only origin stable-15jun
git status --short

$CommitSha = (git rev-parse HEAD).Trim().ToLowerInvariant()
git branch --show-current
docker compose up -d --build
docker compose ps
```

Não prossiga se `git status --short` produzir saída, a branch não for
`stable-15jun`, o SHA divergir do aprovado ou algum serviço não estiver
saudável.

## Validação antes da execução

No checkout completo:

```powershell
pytest -q backend/tests `
    -k "pre_prod_dividends or proventos"

ruff check backend/app backend/tests
python -m compileall -q backend/app backend/tests
git diff --check
```

Registre os totais na Issue #226. Uma falha interrompe a janela; não ajuste o
banco nem ignore testes para prosseguir.

## Entrada oficial para a prova de idempotência

Defina a mesma janela aprovada para as duas execuções:

```powershell
$CommitSha = (git rev-parse HEAD).Trim().ToLowerInvariant()
$StartDate = "AAAA-MM-DD"
$EndDate = "AAAA-MM-DD"
$Confirmation = "EXECUTE-DIVIDENDS-IDEMPOTENCY:$CommitSha"

.\scripts\Invoke-PreProdDividendsIdempotency.ps1 `
    -CommitSha $CommitSha `
    -Confirmation $Confirmation `
    -StartDate $StartDate `
    -EndDate $EndDate

$OperationExitCode = $LASTEXITCODE
```

O wrapper é a única entrada oficial para a dupla controlada. Ele:

- exige branch `stable-15jun` e `HEAD` igual ao SHA informado;
- exige confirmação exata vinculada ao SHA;
- valida a janela antes de Docker, banco ou rede;
- cria dois `run_id` distintos;
- executa a CLI transacional duas vezes, sequencialmente;
- preserva `first.json` e `second.json` em UTF-8 sem BOM;
- executa o comparador somente sobre os arquivos JSON;
- preserva `idempotency.json`;
- não sobrescreve evidências existentes;
- propaga o exit code do comparador.

O diretório padrão é:

```text
artifacts/pre-prod-rebuild/dividends-idempotency-<OPERATION_ID>/
├── first.json
├── second.json
└── idempotency.json
```

Não informe caminho absoluto nem `ArtifactRoot` fora de `artifacts`.

## Contratos e códigos de saída

Cada execução produz `pre-prod-dividends-seed.v1`.

| Código | Significado |
|---:|---|
| `0` | execução concluída e reconciliada |
| `1` | entrada inválida, falha operacional ou resultado não reconciliado |
| `2` | advisory lock indisponível |
| `3` | falha inesperada com mensagem sensível redigida |

O comparador produz `pre-prod-dividends-seed-idempotency.v1`.

| Código | Significado |
|---:|---|
| `0` | idempotência comprovada |
| `1` | evidências válidas, mas divergentes |
| `2` | arquivo ausente, JSON inválido ou contrato incompatível |

## Critérios de sucesso de cada execução

As duas evidências devem apresentar:

- `schema_version=pre-prod-dividends-seed.v1`;
- branch `stable-15jun`, SHA e janela iguais aos aprovados;
- `run_id` distintos;
- fontes principal e complementar explicitamente registradas;
- `ok=true`;
- transação final confirmada;
- zero erros bloqueantes;
- zero duplicidades globais e por carteira;
- zero referências órfãs;
- zero direitos materializados sem elegibilidade;
- zero direitos elegíveis ausentes;
- zero valores inválidos;
- cobertura e agrupamentos determinísticos;
- nenhuma escrita fora de `asset_dividends` e `dividends`.

Resposta vazia legítima deve possuir justificativa explícita. Falha de
transporte, autenticação, HTTP, JSON ou indisponibilidade de provedor não pode
ser convertida em ausência de eventos.

## Critérios da idempotência

Além de `ok=true`, o relatório final deve confirmar:

- mesma versão de contrato, branch, SHA, janela e fronteiras;
- baseline da segunda execução encadeado ao estado final da primeira;
- mesmas contagens finais e mesma cobertura;
- fontes e agrupamentos por classe, tipo, fonte, ano e ticker estáveis;
- zero linhas criadas na segunda execução;
- zero linhas atualizadas na segunda execução;
- zero achados de integridade.

Se a fonte mudar entre as execuções, preserve os arquivos, classifique a prova
como inconclusiva e produza uma nova dupla controlada em outra janela
operacional. Não edite as evidências para fazê-las convergir.

## Critérios de aborto

Interrompa e registre na Issue #226 quando:

- branch, SHA, confirmação ou janela divergirem;
- houver alteração local no checkout;
- a imagem do backend não corresponder ao SHA;
- o advisory lock estiver ocupado;
- um provedor obrigatório falhar ou retornar payload malformado;
- payload vazio não possuir classificação explícita;
- ativo coletado não existir no catálogo autorizado;
- ocorrer colisão conflitante entre fontes;
- aparecer duplicidade, órfão ou direito sem elegibilidade;
- um direito elegível deixar de ser materializado;
- qualquer execução retornar código diferente de `0`;
- o comparador retornar código diferente de `0`;
- qualquer arquivo de evidência estiver ausente, truncado ou inválido.

Não corrija manualmente `asset_dividends` ou `dividends` durante a mesma janela.
O fluxo executa rollback integral quando a divergência ocorre antes do commit.
Após qualquer falha, preserve as evidências existentes, interrompa processos
concorrentes e abra um bloco corretivo separado.

## Evidências a registrar

Na Issue #226, registre:

- SHA, branch e janela;
- ambiente e banco alvo sem dados sensíveis;
- totais da suíte específica, regressão, Ruff e compilação;
- `operation_id` e os dois `run_id`;
- caminhos e SHA-256 de `first.json`, `second.json` e `idempotency.json`;
- exit codes das duas execuções e do comparador;
- contagens `before` e `after`;
- criados, atualizados e inalterados no catálogo e na materialização;
- fontes, cobertura e agrupamentos;
- confirmação de zero duplicidades, órfãos e violações de elegibilidade;
- conclusão objetiva sobre idempotência.

Exemplo para os checksums:

```powershell
Get-FileHash `
    .\artifacts\pre-prod-rebuild\dividends-idempotency-<OPERATION_ID>\*.json `
    -Algorithm SHA256
```

Somente após a reconciliação das três evidências devem ser atualizadas as
Issues #226, #216 e #158. Artefatos operacionais não devem ser versionados.
