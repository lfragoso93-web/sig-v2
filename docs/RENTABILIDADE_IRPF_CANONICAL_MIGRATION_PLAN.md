# Plano de migração canônica — Rentabilidade e IRPF

> Estado inicial: 02/08/2026  
> Issue-mãe: #227  
> Issues de execução: #151 e #56

## Decisão

Rentabilidade e IRPF não podem manter motores próprios de posição, custo médio ou resultado realizado. Ambos devem consumir projeções canônicas compartilhadas e acrescentar somente semântica específica de apresentação ou tributação.

## Inventário confirmado

### `rentabilidade_service.py`

Ainda mantém responsabilidades paralelas:

- consulta e agrupamento próprios de transações;
- posição corrente via `calc_raw_positions`;
- busca e enriquecimento próprios de preços;
- cálculo de custo, patrimônio e PnL não realizado;
- retornos aproximados mensal e de 12 meses;
- cache específico do contrato legado.

Já foram migrados para leitores canônicos:

- resultado realizado;
- capital líquido aportado;
- agregação de proventos.

### IRPF — estado atual

Concluído:

- reader histórico canônico por data de corte;
- Bens e Direitos via `irpf_bens_direitos_service.py`;
- relatório completo via `irpf_report_service.py`;
- regras fiscais extraídas para `irpf_tax_service.py`;
- exportações PDF/CSV extraídas para `irpf_export_service.py`;
- remoção física de `calc_bens_direitos` e do orquestrador duplicado;
- testes arquiteturais contra reintrodução do leitor legado;
- rotas frontend canônicas em `/carteira/irpf`.

Pendente:

- inventário de ganhos mensais concluído em
  `docs/IRPF_MONTHLY_CAPITAL_GAINS_INVENTORY.md`;
- caracterizar e migrar ganhos de capital mensais;
- Day Trade versus Swing Trade;
- isenção mensal;
- compensação de prejuízos;
- retenções;
- ausência cambial explícita, sem fallback silencioso.

## Arquitetura alvo

```text
transactions + eventos corporativos + câmbio persistido
        ↓
projeção canônica de posição e custo por data
        ↓
projeção canônica de realizações por operação/período
        ↓
Rentabilidade: apresentação, snapshots e TWR
IRPF: classificação fiscal, isenções, alíquotas e compensações
```

## Ordem de implementação

### Bloco A — caracterização

1. Cobrir posição histórica por data de corte.
2. Cobrir custo médio e custo total após compras e vendas parciais.
3. Cobrir zeragem e recompra.
4. Cobrir resultado realizado por venda.
5. Cobrir moeda estrangeira com taxa persistida.
6. Provar equivalência entre resultados atuais e projetores canônicos nos cenários suportados.

**Estado:** concluído para Bens e Direitos.

### Bloco B — leitor canônico histórico

1. Extrair ou ampliar um leitor único de posição/custo `as_of`.
2. Integrar eventos corporativos já canônicos sem alterar transações históricas.
3. Expor resultado por ticker e, quando necessário, por operação.
4. Proibir chamadas externas durante a projeção.

**Estado:** reader histórico disponível; extensão por operação ainda poderá ser necessária para ganhos mensais.

### Bloco C — migração de Rentabilidade

1. Substituir `calc_raw_positions` e enriquecimento paralelo.
2. Remover cálculo local de custo e PnL não realizado.
3. Substituir retornos aproximados por contratos canônicos ou ausência explícita.
4. Consolidar invalidação de cache.
5. Preservar contratos públicos.

**Estado:** em andamento na Issue #151.

### Bloco D — migração do IRPF

1. Migrar Bens e Direitos para posição/custo na data de corte — concluído.
2. Inventariar consumidores, reconstruções paralelas e regras fiscais —
   concluído, sem alteração de comportamento.
3. Caracterizar ganhos mensais, Day Trade/Swing Trade, isenção, prejuízos,
   retenções, custos, classes, eventos e câmbio — pendente.
4. Migrar ganho realizado para o leitor canônico — pendente.
5. Manter no IRPF apenas:
   - Day Trade versus Swing Trade;
   - classificação por classe;
   - isenção mensal;
   - alíquotas;
   - compensação de prejuízo;
   - retenções e relatórios.
6. Eliminar fallback cambial silencioso `1.0`; ausência deve ser explícita ou bloqueante.

### Bloco E — remoção do legado

1. Remover consumidores restantes de `rentabilidade_service.py`.
2. Excluir o serviço quando ficar sem uso.
3. Adicionar regressões arquiteturais contra imports e cálculos paralelos.
4. Sincronizar README, ROADMAP, CHANGELOG e arquitetura.

## Validação consolidada

Checkpoint de 02/08/2026:

- backend: `1097 passed`, `22 skipped`, zero warnings;
- Ruff e `compileall`: aprovados;
- frontend: `23` arquivos de teste e `86` testes aprovados;
- typecheck, lint e build: aprovados.

## Critérios de aceite

- uma única projeção de posição e custo por data;
- uma única projeção de resultado realizado;
- nenhuma chamada a provedor no cálculo financeiro;
- Rentabilidade e IRPF reconciliam para o mesmo conjunto de operações;
- eventos corporativos preservam custo e histórico;
- ausência cambial não vira taxa `1.0` silenciosamente;
- suíte completa, Ruff do escopo e `compileall` aprovados;
- #151 encerrada somente após remoção física do serviço legado;
- #56 permanece aberta para a camada de produto e para a migração fiscal mensal.

## Fora deste macrobloco

- interface final avançada do IRPF;
- novas regras tributárias sem requisito validado;
- TWR de Tesouro e Renda Fixa (#149);
- histórico IBOV (#150);
- carga de carteiras reais.
