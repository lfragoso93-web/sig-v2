# Roadmap pós-merge — liberação do lab para testes com seeds

Data: 2026-08-26  
Branch de trabalho: `stable-15jun`  
Base promovida para `main`: PR #290 / `origin/main` em `05f7b34ef48d3993478fbe7f5f757f69706c8e58`

## Estado pós-merge

- As PRs #287 e #290 foram mergeadas com sucesso em `main`.
- A `main` não deve receber desenvolvimento direto; novos blocos continuam em `stable-15jun` e só retornam para `main` após validação.
- Consulta pós-merge não retornou alertas abertos de Code Scanning.
- Consulta pós-merge não retornou alertas abertos de Dependabot security.
- PRs remanescentes após triagem:
  - #291 `stable-15jun -> main`: adiciona validação versionada de contratos de seed e readiness do lab OCI; validada manualmente no lab em `feda80284c3882b2f5614b1d1c6fab752e9a2f8a`; aguarda CI/merge.
  - #289 `typescript 7.0.2`: permanece bloqueada por incompatibilidade de peer dependency com `typescript-eslint`; não aceitar automaticamente.

## Objetivo operacional

Liberar o ambiente OCI lab para testes completos com todos os seeds e bootstraps permitidos, mantendo `ready_for_real_data=false` até certificação explícita dos gates de dados reais.

## Cronograma por criticidade, esforço e utilidade

| Ordem | Bloco | Issues/PRs | Criticidade | Esforço | Utilidade | Critério de saída |
|---:|---|---|---|---|---|---|
| 1 | Manter PR #291 até merge | #291, #284, #216 | Alta | Baixo | Alta | CI/merge concluído; `stable-15jun` realinhada com `main` após merge |
| 2 | Gate de segurança recorrente | #269 | Alta | Baixo | Alta | Code Scanning, Dependabot, Gitleaks, Trivy, pip-audit e npm audit verdes/sem alertas abertos |
| 3 | Certificação de contratos de seeds sem execução real | #216, #226, #158 | P0 | Médio | Máxima | `scripts/oci_seed_contract_validation.sh` aprovado no lab sem executar seed real |
| 4 | Readiness integrado do lab OCI | #284, #216, #227 | P0 | Baixo/Médio | Máxima | `scripts/oci_lab_seed_readiness_check.sh` aprovado; `/ready` preserva `ready_for_real_data=false` |
| 5 | Ensaio de bootstrap completo com dados descartáveis | #227, #216, #158, #253 | P0 | Alto | Máxima | Execução lab não real com evidência, sem `ready_for_real_data=true`, sem produção e com smoke pós-restart |
| 6 | Proventos reais: janela controlada | #226, #216, #158 | P0 | Médio/Alto | Máxima | Só após autorização explícita: duas execuções, `first.json`, `second.json`, `idempotency.json` e comparação OK |
| 7 | Central SuperAdmin por etapas | #253 | Alta | Alto | Alta | UI/contrato para estágios nomeados, bloqueios, status e readiness sem endpoints legados |
| 8 | Backup/restore hardening | #83 | Alta | Alto | Alta | Restore seguro, auditável, status persistido e testes em banco descartável |
| 9 | IBOV DB-first | #150 | Média | Médio | Alta | Histórico IBOV persistido, mensalização testada, sem provider no frontend |
| 10 | TWR Tesouro/Renda Fixa | #149 | Alta | Alto | Alta | Cadeia diária por classe com cobertura explícita |
| 11 | Integração BRAPI v2 e providers configuráveis | #130, #127 | Média/Alta | Alto | Alta | Contratos tipados, cobertura por ativo e configuração administrável |
| 12 | Arquitetura posterior | #272, #246, #57, #58, #90, #97 | Média | Médio/Alto | Variável | Entrar somente após lab/seeds estáveis |

## Próximos blocos recomendados

### Bloco A — PR #291 e alinhamento pós-merge

1. Acompanhar CI da PR #291 ou registrar ausência de novo run para o SHA `feda8028`.
2. Após merge, sincronizar `stable-15jun` com `main` por fast-forward, sem reescrever histórico.
3. Reexecutar `sh scripts/oci_lab_seed_readiness_check.sh` no lab alinhado.
4. Manter #289 como gate separado: TypeScript 7 exige validação de compatibilidade com `typescript-eslint`, Vite e toolchain.

### Bloco B — Validação dos seeds sem dados reais

Rodar, em containers temporários ou ambiente CI-equivalente, as suítes focadas.
No lab OCI, a entrada versionada é:

```sh
sh scripts/oci_seed_contract_validation.sh
```

Ela cobre:

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

Depois do readiness integrado passar:

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

O lab já passou no readiness integrado sem dados reais. O próximo desenvolvimento é manter a PR #291 até merge e, em seguida, iniciar o ensaio completo com dados sintéticos/descartáveis. O sistema está saudável para testes de lab, mas ainda não deve ser declarado pronto para dados reais até os gates de seed completo, evidências e autorização formal terminarem.
