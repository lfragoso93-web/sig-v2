# Provedores e fontes de dados

> Última atualização: 14/07/2026

Este documento descreve a política de uso de fontes externas sem transformar provedores em dependência direta das telas.

---

## Princípio

As fontes externas alimentam o banco. As páginas e cálculos financeiros leem dados persistidos.

```text
Fonte externa
        ↓
Integração / sync
        ↓
Banco
        ↓
Snapshots e KPIs
```

---

## Papéis das fontes

| Papel | Uso |
|---|---|
| Fonte principal nacional | Ações, BDRs, ETFs nacionais, FIIs, proventos e cotações locais |
| Fonte internacional | Stocks e ETFs internacionais |
| Fallback internacional | Complemento quando a fonte internacional primária falha ou não cobre a janela |
| Fonte dedicada de Tesouro | Catálogo, preços atuais e histórico de Tesouro Direto |
| Fonte pública complementar | Fallback para alguns títulos ou indicadores quando a fonte dedicada não cobre |
| Fontes macroeconômicas | CDI, Selic, IPCA, IGP-M e câmbio |

---

## Estratégia por classe

| Classe | Estratégia atual |
|---|---|
| Ação | Fonte principal nacional, histórico máximo quando disponível |
| ETF nacional | Fonte principal nacional, histórico máximo quando disponível |
| BDR | Fonte principal nacional, fallback controlado |
| FII | Rota dedicada, janela explícita quando a documentação não oferece histórico máximo |
| Stock | Fonte internacional, fallback controlado com histórico máximo |
| ETF internacional | Fonte internacional, fallback controlado com histórico máximo |
| Cripto | Roteamento definitivo em revisão |
| Tesouro Direto | Serviço dedicado, fora do pipeline genérico |
| Renda Fixa | Motor interno, sem cotação externa genérica |

---

## Histórico máximo

Quando a lacuna é de início de série, o sistema solicita o máximo histórico suportado pela fonte.

Exemplos de comportamento:

- fonte nacional com suporte a `range=max`;
- biblioteca internacional com `period=max`;
- rotas sem suporte documentado a histórico máximo permanecem com `startDate` e `endDate`.

Não usar datas artificiais muito antigas quando o provedor oferece uma opção de histórico máximo.

---

## Fallback

Fallback não deve ser automático para todos os casos. Ele precisa respeitar:

- tipo de ativo;
- fonte que já respondeu;
- status persistido;
- quantidade de tentativas;
- erro retornado;
- existência de histórico anterior.

Exemplo de regra:

```text
fonte principal retornou histórico válido, mas não anterior ao início real do ativo
        ↓
marcar HISTORY_START_EXHAUSTED
        ↓
não chamar fallback só para confirmar ausência antes do início real
```

---

## Metadados de provedor

Cada ativo pode persistir:

```text
provider
provider_symbol
provider_status
provider_last_sync_at
provider_last_error
provider_attempts
```

Esses campos reduzem:

- chamadas de descoberta repetidas;
- fallback desnecessário;
- histórico máximo baixado várias vezes;
- ruído em logs.

---

## Símbolo do provedor

`provider_symbol` pode diferir do ticker contábil.

Exemplos conceituais:

```text
Ticker contábil fracionário → ticker-base de preço
Nome completo de cripto     → código de mercado
Título de Tesouro           → slug canônico dedicado
```

O ticker original da transação deve ser preservado.

---

## Status de provedor

| Status | Significado |
|---|---|
| `PENDING` | Ainda não sincronizado ou aguardando nova tentativa |
| `OK` | Última sincronização útil terminou sem erro |
| `FAILED` | Última tentativa falhou |
| `HISTORY_START_EXHAUSTED` | Provedor já entregou o máximo anterior disponível |

---

## Logs esperados

Logs devem priorizar resumo por ativo:

```text
ativo=X ranges=1 received=2000 inserted=120 source=principal symbol=X
```

Para preços rejeitados:

```text
precos rejeitados ticker=X quantidade=35 source=fallback intervalo=...
```

Evitar um warning por linha quando o problema é repetitivo.

---

## Pendências

- Provider router definitivo por capacidade.
- Fallback baseado em falhas recorrentes e cobertura real.
- Uso em lote da rota histórica quando a fonte suportar múltiplos símbolos.
- Roteamento definitivo de cripto após validação da cobertura atual.
- Consumo de Tesouro nos snapshots por meio do histórico dedicado.
