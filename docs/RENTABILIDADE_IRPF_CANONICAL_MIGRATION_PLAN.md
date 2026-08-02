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

### `irpf_service.py`

Ainda reconstrói diretamente:

- posição em 31 de dezembro;
- custo médio ponderado;
- baixa proporcional do custo em vendas;
- resultado realizado por operação;
- conversão cambial por transação;
- agrupamento mensal de ganhos.

As regras fiscais devem permanecer, mas a reconstrução contábil deve ser removida.

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

### Bloco B — leitor canônico histórico

1. Extrair ou ampliar um leitor único de posição/custo `as_of`.
2. Integrar eventos corporativos já canônicos sem alterar transações históricas.
3. Expor resultado por ticker e, quando necessário, por operação.
4. Proibir chamadas externas durante a projeção.

### Bloco C — migração de Rentabilidade

1. Substituir `calc_raw_positions` e enriquecimento paralelo.
2. Remover cálculo local de custo e PnL não realizado.
3. Substituir retornos aproximados por contratos canônicos ou ausência explícita.
4. Consolidar invalidação de cache.
5. Preservar contratos públicos.

### Bloco D — migração do IRPF

1. Migrar Bens e Direitos para posição/custo na data de corte.
2. Migrar ganho realizado para o leitor canônico.
3. Manter no IRPF apenas:
   - Day Trade versus Swing Trade;
   - classificação por classe;
   - isenção mensal;
   - alíquotas;
   - compensação de prejuízo;
   - retenções e relatórios.
4. Eliminar fallback cambial silencioso `1.0`; ausência deve ser explícita ou bloqueante.

### Bloco E — remoção do legado

1. Remover consumidores restantes de `rentabilidade_service.py`.
2. Excluir o serviço quando ficar sem uso.
3. Adicionar regressões arquiteturais contra imports e cálculos paralelos.
4. Sincronizar README, ROADMAP, CHANGELOG e arquitetura.

## Critérios de aceite

- uma única projeção de posição e custo por data;
- uma única projeção de resultado realizado;
- nenhuma chamada a provedor no cálculo financeiro;
- Rentabilidade e IRPF reconciliam para o mesmo conjunto de operações;
- eventos corporativos preservam custo e histórico;
- ausência cambial não vira taxa `1.0` silenciosamente;
- suíte completa, Ruff do escopo e `compileall` aprovados;
- #151 encerrada somente após remoção física do serviço legado;
- #56 permanece aberta para a camada de produto, mas o backend fiscal fica canônico.

## Fora deste macrobloco

- interface final do IRPF;
- exportações avançadas;
- novas regras tributárias sem requisito validado;
- TWR de Tesouro e Renda Fixa (#149);
- histórico IBOV (#150);
- carga de carteiras reais.
