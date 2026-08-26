# Roadmap pós-merge — liberação do lab para testes com seeds

Data: 2026-08-26  
Branch de trabalho: `stable-15jun`  
Base promovida para `main`: PR #287 / `origin/main` em `7a50cc307d54f91fa4c63cd50aedc6b70cff97b6`

## Estado pós-merge

- A PR #287 foi mergeada com sucesso em `main`.
- A `main` não deve receber desenvolvimento direto; novos blocos continuam em `stable-15jun` e só retornam para `main` após validação.
- Consulta pós-merge não retornou alertas abertos de Code Scanning.
- Consulta pós-merge não retornou alertas abertos de Dependabot security.
- PRs Dependabot superseded/remanescentes devem ser tratadas após triagem:
  - #280 `lucide-react`: conteúdo já consolidado pela #287; candidata a fechamento como superseded.
  - #235 `hadolint-action`: conteúdo já consolidado pela #287 e CI ajustado; candidata a fechamento como superseded.
  - #288 `eslint 10.9.0`: nova atualização pós-merge; baixo risco, validar em bloco pequeno.
  - #289 `typescript 7.0.2`: nova atualização major pós-merge; alto risco de compatibilidade, não aceitar automaticamente.

## Objetivo operacional

Liberar o ambiente OCI lab para testes completos com todos os seeds e bootstraps permitidos, mantendo `ready_for_real_data=false` até certificação explícita dos gates de dados reais.

## Cronograma por criticidade, esforço e utilidade

| Ordem | Bloco | Issues/PRs | Criticidade | Esforço | Utilidade | Critério de saída |
|---:|---|---|---|---|---|---|
| 1 | Higiene pós-merge e PRs superseded | #280, #235, #288, #289 | Alta | Baixo/Médio | Alta | PRs obsoletas fechadas; #288 validada ou absorvida; #289 classificada como major gateado |
| 2 | Sincronizar `stable-15jun` com a `main` mergeada | #284 | Alta | Baixo | Alta | Branch de desenvolvimento alinhada ao merge commit sem reescrever histórico |
| 3 | Gate de segurança recorrente | #269 | Alta | Baixo | Alta | Code Scanning, Dependabot, Gitleaks, Trivy, pip-audit e npm audit verdes/sem alertas abertos |
| 4 | Certificação de contratos de seeds sem execução real | #216, #226, #158 | P0 | Médio | Máxima | Suítes focadas de FX, macro, Tesouro, B3, proventos e bootstrap completo passando no lab |
| 5 | Ensaio de bootstrap completo com dados descartáveis | #227, #216, #158, #253 | P0 | Alto | Máxima | Execução lab não real com evidência, sem `ready_for_real_data=true`, sem produção e com smoke pós-restart |
| 6 | Proventos reais: janela controlada | #226, #216, #158 | P0 | Médio/Alto | Máxima | Só após autorização explícita: duas execuções, `first.json`, `second.json`, `idempotency.json` e comparação OK |
| 7 | Central SuperAdmin por etapas | #253 | Alta | Alto | Alta | UI/contrato para estágios nomeados, bloqueios, status e readiness sem endpoints legados |
| 8 | Backup/restore hardening | #83 | Alta | Alto | Alta | Restore seguro, auditável, status persistido e testes em banco descartável |
| 9 | IBOV DB-first | #150 | Média | Médio | Alta | Histórico IBOV persistido, mensalização testada, sem provider no frontend |
| 10 | TWR Tesouro/Renda Fixa | #149 | Alta | Alto | Alta | Cadeia diária por classe com cobertura explícita |
| 11 | Integração BRAPI v2 e providers configuráveis | #130, #127 | Média/Alta | Alto | Alta | Contratos tipados, cobertura por ativo e configuração administrável |
| 12 | Arquitetura posterior | #272, #246, #57, #58, #90, #97 | Média | Médio/Alto | Variável | Entrar somente após lab/seeds estáveis |

## Próximos blocos recomendados

### Bloco A — Higiene pós-merge

1. Confirmar CI da `main` e alertas de segurança.
2. Fechar #280 e #235 como superseded pela #287, se não houver divergência pendente.
3. Tratar #288 em `stable-15jun` com build frontend e smoke OCI.
4. Manter #289 como gate separado: TypeScript 7 exige validação de compatibilidade com `typescript-eslint`, Vite e toolchain.

### Bloco B — Validação dos seeds sem dados reais

Rodar, em containers temporários ou ambiente CI-equivalente, as suítes focadas:

- `pre_prod_fx_seed`;
- `pre_prod_macro_seed`;
- `pre_prod_treasury_seed`;
- `pre_prod_b3_seed`;
- `pre_prod_dividends_seed`;
- `system_bootstrap`;
- `asset_bootstrap`.

Critérios:

- não executar seed real;
- não gravar artefatos versionados;
- não imprimir segredos;
- não alterar `.env`;
- não mudar `ready_for_real_data`;
- registrar bugs em commits pequenos na `stable-15jun`.

### Bloco C — Ensaio lab com dados descartáveis

Depois das suítes passarem:

1. Criar usuário/carteira lab descartável.
2. Inserir operações sintéticas representativas.
3. Rodar estágios de bootstrap permitidos em modo lab/teste, quando houver entrada segura.
4. Validar telas de patrimônio, rentabilidade, proventos, IRPF e administração.
5. Executar smoke OCI e restart/recreate dos containers.

### Bloco D — Janela real controlada futura

Somente após autorização explícita nas issues/runbooks:

- executar proventos reais da #226 com duas rodadas e comparação offline;
- preservar evidências fora do versionamento;
- atualizar issues #216/#226/#158 com SHA, janela, contagens e checksums;
- somente então reavaliar `ready_for_real_data`.

## Decisão atual

O melhor próximo desenvolvimento é implementar/validar o Bloco A e depois o Bloco B. O sistema está saudável para testes de lab, mas ainda não deve ser declarado pronto para dados reais até os gates de seed completo e evidências terminarem.
