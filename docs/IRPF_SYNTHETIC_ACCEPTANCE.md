# Gate sintético de aceitação fiscal do IRPF

## Contexto

A base local atual não possui carteiras com operações reais suficientes para
validar a CLI integrada por competência. Uma execução sobre carteira/ano vazio é
válida operacionalmente, mas não comprova correção fiscal nem equivalência entre
motores.

Enquanto não existir uma base real autorizada, a Issue #56 usa um corpus
sintético determinístico como gate complementar. Esse corpus não substitui a
homologação futura com operações reais e não deve ser interpretado como prova de
equivalência com `calc_ganhos_capital`.

## Contrato versionado

Arquivo:

`backend/tests/fixtures/irpf_synthetic_acceptance_v1.json`

Schema:

`irpf-synthetic-acceptance.v1`

O corpus contém entradas financeiras e resultados fiscais esperados. Os valores
esperados são revisáveis em código e independem de banco, rede ou dados de
usuário.

## Cenários cobertos

- ações exatamente no limite mensal de isenção;
- ações acima do limite mensal;
- BDR tributável sem herdar isenção de ações;
- FII com alíquota de 20%;
- prejuízo de ETF transportado e consumido cronologicamente;
- Day Trade positivo tributado a 20%;
- prejuízo Day Trade compensado somente no bucket Day Trade.

## Pipeline exercitado

O teste `test_irpf_synthetic_acceptance_matrix.py` executa os módulos canônicos
reais:

1. adaptação de `CanonicalRealizedDisposal` para entrada fiscal;
2. agrupamento mensal por classe fiscal;
3. aplicação de isenção e alíquota comum;
4. compensação segregada de prejuízos comuns;
5. apuração mensal de Day Trade e compensação própria.

O teste não usa o legado como oráculo, pois comportamentos legados já conhecidos
podem estar fiscalmente incorretos.

## Limitações explícitas

O corpus atual não cobre:

- IRRF e retenções;
- DARF mínima e acumulação de imposto inferior ao mínimo;
- câmbio e ativos no exterior;
- eventos corporativos;
- persistência de saldos entre anos-calendário;
- homologação com notas de corretagem ou declarações reais.

Esses itens permanecem gates próprios da Issue #56.

## Regra de evolução

Toda nova regra fiscal ou anomalia corrigida deve adicionar um cenário
versionado antes da alteração de runtime. O corpus deve manter expectativas
monetárias determinísticas e não pode depender de fallback externo.
