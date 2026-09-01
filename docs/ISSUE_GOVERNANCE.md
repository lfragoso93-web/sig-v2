# Governança de Issues — SGI v2

> Documento canônico para organização, consolidação e encerramento do backlog do SGI v2.

## Objetivo

Manter o backlog pequeno, legível e acionável antes e durante a fase de testes funcionais, evitando Issues duplicadas, sobrepostas ou obsoletas.

## Taxonomia

### Gate

Issue que controla autorização operacional ou readiness. Permanece aberta enquanto o bloqueio existir, mesmo que parte da implementação esteja concluída.

Exemplos atuais: #227, #158, #216, #226, #284.

### Macroprojeto

Issue que concentra uma evolução funcional/arquitetural ampla e pode absorver escopos historicamente separados.

Exemplo atual: #246 passa a ser a Issue canônica do macroprojeto Metas + Análise de Carteira, absorvendo #57.

### Feature

Entrega funcional independente que não precisa controlar outras Issues.

Exemplos atuais: #58, #90, #97, #149, #150, #253.

### Arquitetura / plataforma

Evolução transversal que habilita várias features, sem ser por si só um gate de dados reais.

Exemplos atuais: #127, #130.

### Dívida técnica

Correção estrutural conhecida sem comportamento de produto novo.

Exemplos atuais: #83, #269, #272.

### Bug / gap de teste

Finding reproduzível descoberto na fase de testes. Deve ter escopo pequeno, severidade/impacto, passos de reprodução e critério de aceite. Não deve ser escondido dentro de macroprojeto quando exigir correção independente.

## Regras de consolidação

1. fechar como `duplicate` somente quando todo o escopo útil estiver preservado em outra Issue canônica;
2. antes de fechar, atualizar a Issue canônica com entregas, critérios e dependências que seriam perdidos;
3. gates não devem ser fechados apenas porque a implementação terminou; fechar somente quando o gate operacional também estiver satisfeito;
4. Issues-mãe devem funcionar como índice e não repetir detalhes operacionais de todas as filhas;
5. uma feature não deve permanecer aberta só para servir de referência histórica se o trabalho já estiver integralmente absorvido;
6. novas descobertas da fase de testes devem preferir Issues pequenas e específicas;
7. não criar nova Issue quando uma Issue canônica existente já cobrir integralmente o trabalho;
8. documentação e Issue devem refletir o mesmo estado real.

## Hierarquia vigente

### Dados reais / pré-produção

- #227 — gate-mãe de arquitetura/readiness;
- #158 — reconstrução e sequência operacional da base;
- #216 — gate agregado de seeds isolados;
- #226 — Proventos;
- #284 — certificação/migração OCI.

Enquanto esses gates estiverem ativos, eles permanecem separados porque governam decisões operacionais distintas.

### Providers / dados de mercado

- #130 — evolução técnica da integração BRAPI e enriquecimento;
- #127 — configuração dinâmica de providers pelo SuperAdmin;
- #253 — UI/orquestração operacional do bootstrap.

Essas Issues são relacionadas, mas não duplicadas: #130 trata contratos/capabilities de integração; #127 trata configuração administrativa; #253 trata execução/visualização do bootstrap.

### Metas + Análise de Carteira

- #246 — Issue canônica do macroprojeto completo;
- #57 — escopo histórico absorvido por #246 e deve permanecer fechado como duplicado após consolidação.

### Features independentes

- #58 — Janela Global do Ativo;
- #90 — UX de Patrimônio;
- #97 — Google OAuth;
- #149 — TWR Tesouro/Renda Fixa;
- #150 — histórico persistido do IBOV.

### Dívidas técnicas

- #83 — Backup/Restore administrativo;
- #269 — Code Scanning e vulnerabilidades abertas;
- #272 — aliases físicos legados de `corporate_events`.

## Processo de sanitização

A Issue #293 acompanha a sanitização do backlog.

Cada rodada deve:

1. inventariar Issues abertas;
2. classificar pela taxonomia acima;
3. detectar duplicidade/sobreposição;
4. escolher a Issue canônica;
5. mover o escopo útil para a canônica;
6. fechar a redundante com motivo explícito;
7. registrar o resultado na #293;
8. não misturar essa operação com implementação funcional.

## Entrada da fase de testes

Quando a fase de testes funcionais começar, bugs e gaps deverão ser registrados como Issues específicas, com:

- comportamento esperado;
- comportamento observado;
- passos de reprodução;
- ambiente/SHA;
- severidade/impacto;
- evidências;
- critério de aceite;
- relação com macroprojeto existente, quando houver.
