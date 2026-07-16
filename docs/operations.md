# Operação — SGI v2

> Última atualização: 14/07/2026

Este guia descreve os comandos de manutenção, validação e diagnóstico do SGI v2.

---

## Subir o ambiente

```bash
cp .env.example .env
docker compose up -d --build
```

Ver logs do backend:

```bash
docker compose logs -f backend
```

---

## Rebuild completo de mercado

Comando oficial:

```bash
python -m app.cli.full_market_rebuild
```

Via Docker Compose:

```bash
docker compose exec backend python -m app.cli.full_market_rebuild
```

PowerShell com arquivo de log:

```powershell
$LogFile = ".\full-market-rebuild-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"

docker compose exec backend python -m app.cli.full_market_rebuild 2>&1 |
    Tee-Object -FilePath $LogFile
```

---

## O que o rebuild executa

1. Reconciliar catálogo de ativos.
2. Auditar cobertura histórica de preços.
3. Sincronizar lacunas reais.
4. Atualizar Tesouro Direto.
5. Atualizar benchmarks.
6. Sincronizar e materializar proventos.
7. Reconstruir snapshots TWR.
8. Gerar auditoria final de cobertura.

---

## Leitura do resultado

Resultado esperado:

```json
{
  "ok": true,
  "steps": [
    {"name": "catalog_and_asset_prices", "ok": true},
    {"name": "treasury", "ok": true},
    {"name": "benchmarks", "ok": true},
    {"name": "proventos", "ok": true},
    {"name": "twr_snapshots", "ok": true},
    {"name": "final_coverage_audit", "ok": true}
  ]
}
```

Se uma etapa retorna `errors`, `assets_failed` ou lista de erros, o rebuild deve terminar com `ok=false`, mesmo que as demais etapas concluam.

---

## Sinais saudáveis

Durante uma execução saudável:

- não há `QueuePool limit reached`;
- snapshots TWR terminam em segundos ou poucos minutos;
- proventos materializam sem erro de limite de parâmetros;
- preços inválidos são rejeitados antes do banco;
- lacunas antigas já esgotadas não são repetidas;
- chamadas externas diminuem em execuções subsequentes.

---

## Sinais de atenção

| Sinal | Interpretação |
|---|---|
| `NumericValueOutOfRangeError` | Preço anômalo passou pela validação |
| `number of query arguments cannot exceed 32767` | Alguma materialização voltou a usar lote grande demais |
| `QueuePool limit reached` | Sessões longas ou concorrência excessiva |
| Muitos `startDate=1900-01-01` | Histórico máximo não está sendo usado ou smart sync não persistiu estado |
| Muitos fallbacks lentos | Roteador ainda está tentando fonte incompatível |
| `has_partial_prices=true` persistente | Cobertura de preços insuficiente ou classe sem roteamento correto |

---

## Validação depois de mudanças estruturais

1. Rebuild da imagem:

```bash
docker compose up -d --build backend
```

2. Executar manutenção:

```bash
docker compose exec backend python -m app.cli.full_market_rebuild
```

3. Conferir logs:

```bash
docker compose logs -f --since 10m backend
```

4. Validar no frontend:

- Resumo;
- Patrimônio;
- Rentabilidade;
- Proventos;
- importação CSV.

---

## Scheduler

A rotina diária deve respeitar a ordem:

```text
sincronizar dados
        ↓
materializar proventos
        ↓
reconstruir snapshots
        ↓
servir KPIs
```

Se os horários forem alterados, preserve a dependência lógica.

---

## Quando rodar `full_market_rebuild`

- Após importação CSV grande.
- Após mudança estrutural no cálculo de rentabilidade.
- Após migration de dados canônicos.
- Após correção de provedor ou histórico de preços.
- Antes de validar Resumo, Patrimônio e Rentabilidade.
- Antes de abrir PR estrutural para `main`.

---

## Observação sobre PowerShell

O PowerShell pode exibir `NativeCommandError` quando o processo escreve em `stderr`, mesmo sem falha real. A fonte de verdade é o JSON final e o código de saída do comando.
