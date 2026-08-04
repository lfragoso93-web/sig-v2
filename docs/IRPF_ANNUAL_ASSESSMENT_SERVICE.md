# Serviço e CLI da apuração anual canônica de IRPF

## Objetivo

Este documento descreve os blocos 4N e 4O da Issue #56.

O serviço `irpf_annual_assessment_service.py` executa a apuração integrada e
retorna diretamente o contrato interno versionado
`irpf-annual-assessment.v1`.

A CLI `app.cli.irpf_annual_assessment` oferece uma forma operacional e
read-only de inspecionar esse contrato antes da criação de qualquer endpoint
público.

## Serviço read-only

A função `build_irpf_annual_assessment`:

1. recebe sessão, carteira e ano-calendário;
2. executa uma única vez `assess_annual_integrated_operations`;
3. converte o resultado por `map_annual_integrated_assessment`;
4. devolve `IrpfAnnualAssessmentContract`.

O serviço não:

- persiste dados;
- abre nova sessão;
- recalcula regras fora da apuração integrada;
- altera consumidores legados;
- expõe endpoint HTTP.

## CLI interna

Uso no container backend:

```bash
python -m app.cli.irpf_annual_assessment --portfolio-id 1 --year 2024
```

Comportamento:

- valida carteira positiva e ano entre 1900 e 9999;
- abre sessão assíncrona;
- executa o serviço canônico;
- realiza rollback explícito;
- imprime JSON UTF-8 ordenado;
- preserva valores decimais como strings;
- retorna `0` em sucesso, `1` em erro operacional e `130` em interrupção.

Contrato de erro:

```text
irpf-annual-assessment-error.v1
```

## Fronteira arquitetural

O contrato continua interno. A existência da CLI não transforma o DTO em
schema público nem autoriza seu uso direto pelo frontend.

Antes de publicar uma rota HTTP será necessário:

- definir autorização e isolamento de carteira;
- decidir serialização monetária pública;
- versionar schema de API separado, se necessário;
- revisar compatibilidade com o frontend e exportações.

## Testes protegidos

- uma única execução da apuração integrada;
- uma única conversão para o contrato;
- emissão JSON do contrato v1;
- rollback explícito;
- validação de carteira e ano.
