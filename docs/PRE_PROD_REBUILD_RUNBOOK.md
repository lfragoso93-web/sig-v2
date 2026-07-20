# Runbook de rebuild pré-produção — SGI v2

> Issue-mãe: #158  
> Bloco de preparação: #176  
> Última atualização: 20/07/2026

## Objetivo

Executar a primeira reconstrução limpa da base canônica de forma reversível, auditável e idempotente antes do go-live.

Este runbook trata da operação controlada de pré-produção. A futura interface administrativa de backup e restore permanece no escopo da Issue #83 e não deve duplicar os comandos ou regras definidos aqui.

## Princípios obrigatórios

- Nenhuma limpeza sem backup validado e teste de leitura do arquivo.
- Nenhuma operação destrutiva antes de um dry-run aprovado.
- Usuários, autenticação, configurações e segredos não são removidos.
- Transações e carteira devem ser exportadas e validadas antes da limpeza.
- Dados reconstruíveis devem ser recriados exclusivamente pelos pipelines canônicos.
- Cada etapa deve produzir contagens, duração, erros e ativos não resolvidos.
- Uma falha interrompe a sequência; etapas posteriores não devem mascarar erro anterior.

## Política oficial de classificação

A fonte executável da política é `TABLE_POLICIES`, em `pre_prod_inventory_service.py`. Cada tabela recebe classificação e justificativa no relatório `pre-prod-inventory.v2`.

### Preservar

- `alembic_version`;
- `app_configs`;
- `audit_logs`;
- `goal_allocations`;
- `goals`;
- `irpf_losses`;
- `irpf_records`;
- `irpf_reports`;
- `portfolio_class_targets`;
- `portfolios`;
- `system_configs`;
- `users`.

Essas tabelas contêm estrutura aplicada, identidade, configuração, preferências, trilha de auditoria ou histórico fiscal não integralmente regenerável.

### Exportar antes de qualquer limpeza

- `corporate_events`;
- `fixed_income_investments`;
- `transactions`.

Eventos corporativos podem conter estado aplicado e dados brutos; renda fixa contém condições contratuais; transações formam o livro-razão financeiro. Nenhuma delas pode ser perdida ou presumida como regenerável.

### Reconstruir

- `asset_aliases`;
- `asset_dividends`;
- `asset_prices`;
- `assets`;
- `dividends`;
- `dividends_sync_jobs`;
- `fx_rates`;
- `portfolio_class_snapshots`;
- `portfolio_positions`;
- `portfolio_snapshots`;
- `rate_history`.

Essas tabelas possuem fonte oficial, pipeline idempotente ou são projeções derivadas dos dados preservados/exportados.

Qualquer tabela nova ou desconhecida permanece `unclassified`, faz o CLI retornar código diferente de zero e exige revisão arquitetural antes da limpeza.

## Artefatos obrigatórios

Criar uma pasta por execução:

```text
artifacts/pre-prod-rebuild/YYYYMMDD-HHMMSS/
```

Ela deve conter:

- `database.dump` ou backup SQL equivalente;
- checksum do backup;
- inventário de tabelas e contagens antes da execução;
- exportação validada da carteira;
- relatório de dry-run;
- logs de cada etapa;
- inventário e contagens depois da execução;
- relatório de reconciliação;
- lista de ativos não resolvidos.

Esses artefatos não devem ser versionados no Git.

## Sequência operacional

### 1. Congelar a referência

- confirmar branch `stable-15jun`;
- registrar SHA executado;
- confirmar migrations aplicadas;
- impedir importações ou alterações concorrentes durante a janela.

### 2. Gerar e validar backup

O backup deve incluir esquema e dados. A validação mínima exige:

- comando concluído com código zero;
- arquivo não vazio;
- checksum registrado;
- listagem do conteúdo possível;
- teste de restauração em banco isolado antes da limpeza real.

### 3. Exportar a carteira

- exportar todas as transações e vínculos necessários;
- validar cabeçalhos, encoding, datas, decimais e identificadores;
- comparar contagens do arquivo com o banco;
- bloquear a execução se houver divergência.

### 4. Executar dry-run

```powershell
docker compose exec backend python -m app.cli.pre_prod_inventory
```

O dry-run não pode escrever nem excluir dados. Deve informar:

- classificação e justificativa por tabela;
- contagens atuais por tabela;
- ativos/aliases ambíguos;
- preços órfãos;
- snapshots inconsistentes;
- totais por política;
- confirmação explícita de ausência de escrita.

### 5. Aprovar ou abortar

Abortar se ocorrer qualquer uma das condições:

- backup não restaurável;
- exportação da carteira divergente;
- tabela de usuário/configuração classificada para limpeza;
- qualquer tabela `unclassified`;
- ativos não resolvidos sem tratamento explícito;
- migrations pendentes;
- dry-run com erro ou escrita detectada.

### 6. Executar a limpeza controlada

Somente após aprovação explícita do relatório. A implementação deve usar uma lista permitida de dados reconstruíveis e transação de banco sempre que tecnicamente possível.

### 7. Recriar dados canônicos

Ordem:

1. catálogo e aliases;
2. B3 COTAHIST;
3. Tesouro oficial;
4. benchmarks e câmbio;
5. eventos e proventos;
6. importação da carteira;
7. posições e custos médios;
8. snapshots consolidados e por classe;
9. auditoria final.

O comando operacional de rebuild já documentado é:

```powershell
docker compose exec backend python -m app.cli.full_market_rebuild
```

Ele não substitui backup, dry-run, exportação ou limpeza controlada.

## Relatório final mínimo

O relatório deve registrar:

- SHA da aplicação;
- início, fim e duração;
- contagens antes/depois por entidade;
- número de ativos, aliases, preços, proventos, transações e snapshots;
- ativos não resolvidos e motivo;
- divergência monetária entre posições e snapshots;
- cobertura por classe;
- resultado das telas Resumo, Patrimônio, Rentabilidade e Proventos;
- resultado do teste de reimportação CSV;
- decisão final: aprovado, aprovado com ressalvas ou abortado.

## Idempotência

Uma segunda execução, sem novos dados externos ou transações, deve:

- não criar duplicatas;
- não alterar identificadores canônicos sem justificativa;
- manter contagens estáveis, exceto fontes atualizadas;
- reconciliar os mesmos valores financeiros;
- produzir relatório comparável ao anterior.

## Próximo bloco

Gerar backup versionado por execução, checksum SHA-256 e teste de restauração em banco isolado. Nenhuma limpeza será autorizada até a restauração ser validada.
