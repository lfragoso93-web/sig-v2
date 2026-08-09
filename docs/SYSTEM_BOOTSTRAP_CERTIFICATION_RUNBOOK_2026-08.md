# Runbook de certificação operacional do system-bootstrap.v4

Issues: #227, #248, #250  
Branch obrigatória: `stable-15jun`

## Objetivo

Definir a sequência operacional segura para certificar o `system-bootstrap.v4` antes de qualquer alteração de `ready_for_real_data`.

Este runbook **não autoriza** execução de providers por si só. Etapas com gates explícitos continuam exigindo autorização operacional correspondente.

## Pré-condições globais

Antes de qualquer estágio:

1. `git switch stable-15jun`;
2. `git pull --ff-only origin stable-15jun`;
3. working tree limpa;
4. registrar SHA completo de 40 caracteres e `run_id`;
5. Docker `db`, `redis` e `backend` saudáveis;
6. `ready_for_real_data=false`;
7. nenhum job recorrente de catálogo, metadados, Proventos ou eventos corporativos ativo;
8. snapshot/backup operacional válido quando a etapa puder alterar volume relevante de dados;
9. Issue correspondente atualizada antes da execução real.

## Ordem operacional recomendada

### 1. `asset_catalog`

Objetivo: carregar/reconciliar catálogo global de ativos e metadados necessários aos adapters.

Pré-checks:
- banco acessível;
- catálogo atual inventariado;
- providers permitidos somente dentro da janela de bootstrap.

Aprovação:
- execução concluída sem erro bloqueante;
- ativos persistidos sem duplicação de identidade;
- tipos/tickers inválidos registrados e reconciliados;
- segunda execução convergente.

Rollback/bloqueio:
- qualquer erro estrutural de identidade ou duplicação bloqueia avanço.

### 2. `treasury_catalog`

Objetivo: carregar somente títulos reais suportados do Tesouro Direto.

Aprovação:
- catálogo real persistido;
- nenhum item sintético indevidamente persistido;
- segunda execução sem duplicações;
- símbolos canônicos resolvíveis.

### 3. `treasury_reconciliation`

Objetivo: reconciliar transações existentes de Tesouro com símbolos canônicos.

Aprovação:
- `errors=0`;
- `unresolved=0`, salvo exceção explicitamente analisada e documentada;
- nenhum ativo canônico duplicado;
- segunda execução sem novas mutações indevidas.

Qualquer `unresolved` relevante bloqueia a certificação até análise.

### 4. `benchmarks`

Objetivo: carregar séries obrigatórias de taxas/índices persistidos.

Aprovação:
- todas as séries exigidas pelo contrato financeiro presentes;
- cobertura temporal mínima documentada;
- unicidade `(indicator, date)` preservada;
- segunda execução convergente via UPSERT.

### 5. `fx_rates`

Objetivo: carregar USD-BRL pela PTAX oficial e validar integridade.

Aprovação:
- contrato de identidade (`run_id`, branch, SHA) válido;
- advisory lock adquirido corretamente;
- ausência de pares não suportados/duplicados;
- cobertura dentro da janela válida do Real;
- inspeção final sem findings bloqueantes;
- commit somente após inspeção verde.

### 6. `treasury_history`

Objetivo: preencher histórico e snapshot atual do Tesouro Direto.

Aprovação:
- cobertura histórica compatível com os títulos suportados;
- nenhuma duplicação em `asset_prices`;
- snapshot atual coerente;
- falhas de fonte primária/fallback documentadas;
- reexecução sem duplicações físicas.

### 7. `asset_price_history`

Objetivo: preencher histórico global necessário e eliminar gaps bloqueantes.

Aprovação:
- auditoria de cobertura após execução;
- `errors=0`;
- nenhum gap classificado como bloqueante para contratos financeiros;
- constraints de unicidade preservadas;
- segunda execução sem nova solicitação quando a cobertura já estiver completa.

### 8. `asset_dividends`

Gate operacional: **#226**.

Objetivo: carregar Proventos globais em `asset_dividends` sem materializar direitos por carteira.

Requer:
- autorização operacional explícita;
- `SGI_BOOTSTRAP_ENABLE_DIVIDENDS=true` somente durante a janela autorizada;
- inspeção antes/depois;
- advisory lock;
- transação única controlada.

Aprovação:
- `ok=true`;
- integridade sem findings bloqueantes;
- persistência global sem duplicação/conflitos não reconciliados;
- segunda execução convergente;
- nenhuma escrita por carteira.

### 9. `corporate_events`

Gate operacional dedicado; execução real somente após autorização explícita.

Objetivo: carregar eventos corporativos globais para tipos suportados.

Política de fonte:
- BRAPI primária para eventos expostos por contrato estruturado, como bonificações e subscrições;
- Yahoo complementar/fallback para splits/grupamentos enquanto a BRAPI não expuser contrato estruturado/documentado equivalente;
- nunca inferir split apenas por gap de preço.

Aprovação:
- somente `ACAO`, `BDR` e `ETF_NACIONAL` processados;
- `portfolio_id=None`;
- nenhuma mutação de transações históricas;
- advisory lock e transação única respeitados;
- ausência de duplicações de identidade de fonte;
- cobertura por ativo suportado inspecionada e registrada.

## Checkpoint entre estágios

Após cada estágio real:

1. registrar `run_id`, SHA e janela temporal;
2. registrar contadores de criados/atualizados/ignorados/erros;
3. executar inspeção de integridade/cobertura correspondente;
4. atualizar a Issue relacionada;
5. não avançar se houver finding bloqueante;
6. manter `ready_for_real_data=false`.

## Critério para certificação final

`ready_for_real_data=true` só pode ser avaliado após:

- nove estágios concluídos ou formalmente dispensados com justificativa;
- cobertura operacional suficiente registrada por domínio;
- ausência de findings bloqueantes;
- gates #226/#227 reconciliados;
- #248/#250 atualizadas com evidências finais;
- documentação sincronizada;
- checkpoint técnico final verde;
- decisão formal explícita de certificação.

## Regra de rollback

Se qualquer estágio produzir erro de integridade, conflito sem política de reconciliação, duplicação estrutural, cobertura insuficiente bloqueante ou falha transacional:

- interromper a sequência;
- preservar `ready_for_real_data=false`;
- executar rollback quando suportado pela transação do estágio;
- registrar evidência na Issue correspondente;
- corrigir em bloco pequeno antes de retomar do estágio afetado.
