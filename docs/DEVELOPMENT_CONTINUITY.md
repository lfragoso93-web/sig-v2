# Continuidade de desenvolvimento — SGI v2

> Documento obrigatório para iniciar ou retomar qualquer conversa de desenvolvimento.

## Contexto permanente

- Repositório: `lfragoso93-web/sig-v2`.
- Branch obrigatória: `stable-15jun`.
- Nunca desenvolver diretamente na `main`.
- Antes de qualquer alteração, comparar `stable-15jun` com `main`, revisar Issues abertas, PRs abertas e documentação viva.
- Dividir macroblocos em commits pequenos e rastreáveis.
- Ao final de cada bloco informar resumo técnico, impacto arquitetural, testes, SHA completo e próximo bloco.
- Atualizar a Issue correspondente antes e depois da implementação.
- README, ROADMAP, CHANGELOG e documentação arquitetural devem refletir o estado real.

## Decisão vigente

O SGI v2 está em consolidação arquitetural antes de receber dados reais.

Até o encerramento da Issue #227:

- não importar novas carteiras reais;
- não criar novos usuários reais;
- tratar dados atuais como desenvolvimento descartável;
- usar fixtures, factories e bancos descartáveis;
- manter seeds, sincronizações e rebuilds externos explicitamente opt-in;
- não retomar a certificação operacional da #158 antes dos gates arquiteturais.

## Ordem vigente

1. Baseline, documentação e inventário.
2. Rentabilidade e IRPF canônicos — #151 e #56.
3. Eventos corporativos — #129 e partes da #130.
4. IBOV e TWR — #150 e #149.
5. Ingestão, seeds e rebuild determinísticos — #158, #216 e #226.
6. Qualidade estrutural e timestamps UTC — #192.
7. Certificação integral antes da primeira carga real.

## Checklist de início de conversa

1. Ler esta documentação.
2. Consultar a Issue #227 e seus comentários mais recentes.
3. Confirmar branch e HEAD remoto de `stable-15jun`.
4. Comparar `main...stable-15jun` e confirmar ausência de divergência para trás.
5. Consultar Issues relacionadas ao bloco atual.
6. Consultar todas as PRs abertas, inclusive Dependabot.
7. Conferir README, ROADMAP, CHANGELOG e `docs/architecture.md`.
8. Confirmar último resultado de pytest, Ruff e compileall registrado.
9. Não repetir perguntas já respondidas no histórico ou nas Issues.
10. Continuar do próximo bloco objetivo registrado na #227.

## Formato de checkpoint

Cada checkpoint deve registrar:

- escopo concluído;
- arquivos e contratos afetados;
- impacto arquitetural;
- testes executados e resultados;
- todos os SHAs do checkpoint;
- Issues e documentação atualizadas;
- riscos ou pendências;
- recomendação objetiva do próximo bloco;
- HEAD remoto esperado.

## Estado atual do plano

- Última suíte validada: `1095 passed`, `22 skipped`, `52 warnings`.
- `compileall`: aprovado.
- Reader histórico canônico disponível em `historical_position_projection_reader.py`.
- Endpoint `GET /{portfolio_id}/irpf/{year}/bens` usa `irpf_bens_direitos_service.py`.
- O relatório completo usa `irpf_report_service.py`, que compõe Bens e Direitos canônicos com ganhos e rendimentos fiscais ainda existentes.
- O router IRPF usa dependências `Annotated` e tipagem moderna.
- Teste arquitetural `test_no_legacy_irpf_bens_consumers.py` impede novos consumidores do símbolo legado.
- `calc_ganhos_capital` permanece intacto até a caracterização fiscal dedicada.
- A função antiga `calc_bens_direitos` ainda existe fisicamente em `irpf_service.py`, sem consumidores de produção, aguardando remoção isolada após o gate desta etapa.
- Renda Fixa continua preservada por adaptação isolada até existir leitor histórico dedicado da classe.
- Boot de sincronização de mercado permanece desabilitado por padrão.
- Issue-mãe: #227.
- Issues funcionais imediatas: #151 e #56.

## Próximo bloco objetivo

1. Validar Ruff dos testes ajustados e o teste arquitetural de consumidores.
2. Remover fisicamente `calc_bens_direitos` de `irpf_service.py` em commit isolado.
3. Remover imports, constantes e o orquestrador legado que ficarem sem consumidores, sem tocar em `calc_ganhos_capital`.
4. Adicionar teste arquitetural proibindo a redefinição do símbolo removido.
5. Sincronizar README, ROADMAP, CHANGELOG e `docs/architecture.md` ao fechar o corte estrutural.
6. Avaliar PR de promoção para `main` após a suíte completa.
7. Depois iniciar a caracterização de ganhos mensais, sem alterar regras fiscais antes dos testes.

## Prompt mínimo para nova conversa

```text
@GitHub Continue o desenvolvimento do SGI v2 seguindo integralmente
`docs/DEVELOPMENT_CONTINUITY.md` e a Issue #227.

Repositório: lfragoso93-web/sig-v2
Branch obrigatória: stable-15jun

Antes de alterar código:
- confirme o HEAD remoto;
- compare stable-15jun com main;
- leia a #227 e as Issues do bloco atual;
- revise PRs abertas e documentação viva;
- recupere o último checkpoint e prossiga do próximo bloco objetivo.
```
