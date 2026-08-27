# Roadmap pós-merge — liberação do lab para testes com seeds

Data: 2026-08-27
Branch de trabalho: `stable-15jun`
Base promovida para `main`: PR #292 / `origin/main` em `3eeca232a8627f4562544739112d1dde82b879fb`

## Estado pós-merge

- As PRs #287, #290, #291 e #292 foram mergeadas com sucesso em `main`.
- A `main` não deve receber desenvolvimento direto; novos blocos continuam em `stable-15jun` e só retornam para `main` após validação.
- PRs devem ser abertas apenas ao concluir uma issue ou macroalteração relevante; blocos menores podem seguir com commits/pushes rastreáveis na `stable-15jun`.
- Consulta pós-merge não retornou alertas abertos de Code Scanning.
- Consulta pós-merge não retornou alertas abertos de Dependabot security.
- PRs remanescentes após triagem:
  - #289 `typescript 7.0.2`: permanece bloqueada por incompatibilidade de peer dependency com `typescript-eslint`; não aceitar automaticamente.

## Objetivo operacional

Liberar o ambiente OCI lab para testes completos com todos os seeds e bootstraps permitidos, mantendo `ready_for_real_data=false` até certificação explícita dos gates de dados reais.

## Cronograma por criticidade, esforço e utilidade

| Ordem | Bloco | Issues/PRs | Criticidade | Esforço | Utilidade | Critério de saída |
|---:|---|---|---|---|---|---|
| 1 | Manter `stable-15jun` alinhada pós-merge | #284 | Alta | Baixo | Alta | Branch alinhada com `main`; sem PR nova para bloco pequeno |
| 2 | Gate de segurança recorrente | #269 | Alta | Baixo | Alta | Code Scanning, Dependabot, Gitleaks, Trivy, pip-audit e npm audit verdes/sem alertas abertos |
| 3 | Certificação de contratos de seeds sem execução real | #216, #226, #158 | P0 | Médio | Máxima | `scripts/oci_seed_contract_validation.sh` aprovado no lab sem executar seed real |
| 4 | Readiness integrado do lab OCI | #284, #216, #227 | P0 | Baixo/Médio | Máxima | `scripts/oci_lab_seed_readiness_check.sh` aprovado; `/ready` preserva `ready_for_real_data=false` |
| 5 | Jornada HTTP descartável do lab | #227, #216, #158 | P0 | Baixo/Médio | Máxima | `scripts/oci_lab_disposable_http_smoke.sh` aprovado; usuário e FX sintética removidos no cleanup |
| 6 | Ensaio de bootstrap completo com dados descartáveis | #227, #216, #158, #253 | P0 | Alto | Máxima | Execução lab não real com evidência, sem `ready_for_real_data=true`, sem produção e com smoke pós-restart |
| 7 | Proventos reais: janela controlada | #226, #216, #158 | P0 | Médio/Alto | Máxima | Só após autorização explícita: duas execuções, `first.json`, `second.json`, `idempotency.json` e comparação OK |
| 8 | Central SuperAdmin por etapas | #253 | Alta | Alto | Alta | UI/contrato para estágios nomeados, bloqueios, status e readiness sem endpoints legados |
| 9 | Backup/restore hardening | #83 | Alta | Alto | Alta | Restore seguro, auditável, status persistido e testes em banco descartável |
| 10 | IBOV DB-first | #150 | Média | Médio | Alta | Histórico IBOV persistido, mensalização testada, sem provider no frontend |
| 11 | TWR Tesouro/Renda Fixa | #149 | Alta | Alto | Alta | Cadeia diária por classe com cobertura explícita |
| 12 | Integração BRAPI v2 e providers configuráveis | #130, #127 | Média/Alta | Alto | Alta | Contratos tipados, cobertura por ativo e configuração administrável |
| 13 | Arquitetura posterior | #272, #246, #57, #58, #90, #97 | Média | Médio/Alto | Variável | Entrar somente após lab/seeds estáveis |

## Próximos blocos recomendados

### Bloco A — Alinhamento pós-merge contínuo

1. Sincronizar `stable-15jun` com `main` por fast-forward após merges aprovados, sem reescrever histórico.
2. Reexecutar `sh scripts/oci_lab_seed_readiness_check.sh` no lab alinhado.
3. Reexecutar `sh scripts/oci_lab_disposable_http_smoke.sh` antes de blocos funcionais.
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

1. Rodar `sh scripts/oci_lab_disposable_http_smoke.sh`.
2. Expandir gradualmente a jornada sintética para novos endpoints/telas.
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

O lab já passou no readiness integrado e na jornada HTTP descartável sem dados reais. O próximo desenvolvimento é expandir o ensaio sintético por endpoints/telas e escolher uma issue funcional de alto valor somente depois que a jornada descartável cobrir o fluxo principal. O sistema está saudável para testes de lab, mas ainda não deve ser declarado pronto para dados reais até os gates de seed completo, evidências e autorização formal terminarem.
