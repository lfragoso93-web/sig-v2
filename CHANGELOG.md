# Changelog — SGI v2

Todas as mudanças relevantes do projeto são documentadas aqui. O histórico detalhado anterior permanece preservado no Git e nos changelogs datados em `docs/changelog/`.

## [Unreleased] — branch `stable-15jun`

### 12/09/2026 — recuperação local de gates e contrato canônico de Proventos

- a recuperação da #363 passou a usar suíte local completa como ferramenta de descoberta; a PR estrutural #362 permanece fechada/draft durante o saneamento para evitar consumo iterativo de GitHub Actions;
- contratos de snapshot foram alinhados ao writer único `portfolio_snapshot_canonical_twr_service.py`, mantendo `portfolio_snapshot_service.py` restrito à invalidação;
- o contrato vigente de Proventos foi explicitado como `pre-prod-dividends-seed.v2`;
- `asset_dividends` permanece a única persistência canônica de eventos globais de Proventos;
- direitos de carteira são calculados sob demanda a partir das posições históricas, sem materialização por carteira;
- README, ROADMAP e CHANGELOG foram sincronizados para refletir essa fronteira canônica.

### 10/09/2026 — rebaseline de governança e certificação

- `user-test-readiness.v1` consolidado como gate read-only para validação assistida;
- estado registrado: `GO_ASSISTED`, `ready_for_real_data=false`, `/health=200`, `/ready=503`;
- #303 rebaselined para governar o fechamento de `PORTFOLIO-TEST-READY` e o SHA candidato;
- #226, #216, #158 e #227 rebaselined para consumir evidências já certificadas, evitando repetição destrutiva por checklist histórico;
- cadeia de promoção formalizada como #303 → #226 → #216 → #158 → homologação OCI → #227;
- OCI redefinida como ambiente de homologação do SHA exato certificado localmente, não ambiente de desenvolvimento;
- deploy OCI deve confirmar `APP_COMMIT_SHA == git rev-parse HEAD`;
- `/ready=503` permanece comportamento esperado enquanto `ready_for_real_data=false`;
- #58 reclassificada como parcialmente implementada após validação do detalhe de ativo;
- #149 reclassificada como dívida financeira parcial, não blocker automático quando a ausência de TWR é explícita;
- #246 atualizada para reconhecer Metas operacionalmente funcional após migration runtime-safe, preservando o macroprojeto definitivo como futuro;
- #351 classificada como epic pós-GO;
- #352 e #354 identificadas como candidatos P1 se ainda reproduzíveis;
- #353 classificada como P2 por padrão;
- #355–#361 classificados como evolução pós-GO, com #360 precedendo #361;
- README, ROADMAP e CHANGELOG rebaselined para remover baselines históricos tratados como instruções vigentes.

### Evidências funcionais acumuladas

- backend completo anteriormente certificado com `1880 passed, 1 skipped, 10 warnings` no ciclo #303;
- frontend anteriormente certificado com `npm ci`, typecheck, lint, Vitest e build;
- CSV sintético/assistido com dry-run, import, replay, atomicidade e rebuild canônico;
- carteira assistida com 308 transações e 65 ativos distintos;
- rebuild histórico observado com 493 snapshots entre 22/10/2024 e 10/09/2026;
- Proventos portfolio-scoped idempotentes com 49 ativos elegíveis e 183 eventos na janela validada;
- Tesouro DB-first, Renda Fixa dedicada e IRPF para classes suportadas exercitados em runtime;
- eventos corporativos portfolio-scoped disponíveis, com reconciliação material ainda pendente para casos complexos.

### Arquitetura preservada

- `transactions` é a fonte canônica do lifecycle;
- runtime financeiro é DB-first;
- providers ficam fora do read path financeiro;
- `summary.v2`, `rentabilidade.v2`, snapshots e projetores compartilhados continuam contratos canônicos;
- Proventos pertencem ao ativo em `asset_dividends`;
- eventos corporativos pertencem ao ativo em `corporate_events`;
- ausência/cobertura parcial permanecem explícitas e não viram zero/fallback silencioso.

### Pendências para o primeiro GO

1. concluir #303 e congelar SHA;
2. revalidar candidatos P1 #352/#354;
3. decidir/fechar #226;
4. fechar #216;
5. executar o delta final #158;
6. homologar exatamente o mesmo SHA na OCI;
7. #227 emitir GO/NO-GO;
8. somente após GO avaliar `ready_for_real_data=true` e promoção para `main`.

## Histórico

O detalhamento de sanitização arquitetural, segurança, BRAPI/COTAHIST, Proventos, TWR, dependências, OCI e demais microblocos anteriores a este rebaseline permanece disponível no histórico Git e nos documentos datados. A partir deste ponto, este arquivo prioriza marcos de release e governança para evitar que microcommits históricos sejam interpretados como estado operacional atual.
