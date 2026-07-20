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

## Classificação inicial dos dados

### Preservar

- usuários, perfis, autenticação e permissões;
- configurações administrativas e de provedores;
- migrations e metadados estruturais;
- dados que não possam ser regenerados por fonte canônica.

### Exportar e reimportar de forma controlada

- carteiras;
- transações de compra, venda, renda fixa e Tesouro;
- lançamentos manuais não derivados;
- vínculos de propriedade do usuário.

### Reconstruir

- catálogo e aliases canônicos;
- preços B3/COTAHIST;
- catálogo e preços oficiais do Tesouro;
- séries de benchmarks;
- eventos e direitos de proventos materializados;
- posições, custos médios e valuations derivados;
- `PortfolioSnapshot` e `PortfolioClassSnapshot`;
- relatórios de cobertura e reconciliação.

A lista definitiva de tabelas deve ser gerada pelo dry-run a partir dos modelos e migrations atuais. Este documento não autoriza truncamento por nomes presumidos.

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

O dry-run não pode escrever nem excluir dados. Deve informar:

- tabelas preservadas;
- tabelas candidatas à limpeza;
- contagens atuais por tabela;
- dependências e ordem de limpeza;
- ativos/aliases ambíguos;
- preços órfãos;
- snapshots inconsistentes;
- estimativa de volume por pipeline;
- comandos que seriam executados.

### 5. Aprovar ou abortar

Abortar se ocorrer qualquer uma das condições:

- backup não restaurável;
- exportação da carteira divergente;
- tabela de usuário/configuração classificada para limpeza;
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
4. benchmarks;
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

Implementar o comando de inventário e dry-run sem escrita, com saída JSON versionada e testes automatizados. Nenhuma limpeza deve ser implementada no mesmo commit.